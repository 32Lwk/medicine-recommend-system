"""
localhost ルーティング E2E — 実 HTTP 経路検証。

Usage:
  python scripts/routing_e2e_live_runner.py
  python scripts/routing_e2e_live_runner.py --gpt-turns 3 --gpt-sessions 4
  pytest tests/routing/test_routing_e2e_live_integration.py -v -m live
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "routing_e2e_live_scenarios.yaml"
REPORT_DIR = PROJECT_ROOT / "log" / "analysis"
DEFAULT_BASE = "http://127.0.0.1:5000/"
CHAT_TIMEOUT = 180.0
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _kind_route(kind: str, content: str = "", render: str = "") -> str:
    r = (render or "").lower()
    k = (kind or "").lower()
    c = content or ""
    if r == "sage_reco":
        return "Physical"
    if r == "sage_qa":
        return "MedicineQA"
    if k:
        if "concierge" in k or "architecture" in k or "redirect" in k or "greeting" in k:
            return "Concierge"
        if "counseling" in k or "emotional" in k:
            return "Counseling"
        if k == "medicine_qa" or (k.startswith("sage_qa") and "medicine" in k):
            return "MedicineQA"
        if (
            k.startswith("sage_reco")
            or "recommend" in k
            or "physical" in k
            or "symptom" in k
            or k in ("sports_symptom_prompt", "cold_symptom_chip_prompt")
        ):
            return "Physical"
        if k.startswith("sage_qa") or k == "medicine_qa":
            return "MedicineQA"
        if "store" in k:
            return "Store"
        if "session" in k or "memory_delete" in k:
            return "SessionOps"
    if "医薬品相談回答" in c:
        return "MedicineQA"
    if "市販薬" in c or "おすすめ" in c or "推奨" in c:
        return "Physical"
    if any(x in c for x in ("GitHub", "GitLab", "AWS", "GCP", "技術", "インフラ")):
        return "Concierge"
    return "Unknown"


@dataclass
class TurnExpectation:
    user: str
    expect_route: str = "any"
    expect_render: str = "any"
    expect_kind: Optional[str] = None
    must_not_kind: Optional[str] = None
    text_should_contain: list[str] = field(default_factory=list)
    text_must_not_contain: list[str] = field(default_factory=list)
    timeout_s: float = CHAT_TIMEOUT


@dataclass
class LiveScenario:
    id: str
    description: str
    category: str
    turns: list[TurnExpectation]


@dataclass
class TurnResult:
    user: str
    http_status: int
    elapsed_ms: int
    route: str = ""
    render: str = ""
    kind: str = ""
    bot_text: str = ""
    concierge_intent: str = ""
    errors: list[str] = field(default_factory=list)
    passed: bool = True


def _strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def _bot_render(msg: dict) -> str:
    diag = msg.get("diagnosis") or {}
    if isinstance(diag, dict):
        return str(diag.get("render") or "")
    return ""


def _bot_kind(msg: dict) -> str:
    diag = msg.get("diagnosis") or {}
    if isinstance(diag, dict):
        return str(diag.get("kind") or "")
    return ""


def _bot_text(msg: dict) -> str:
    content = str(msg.get("content") or "")
    diag = msg.get("diagnosis") or {}
    parts: list[str] = []
    if content and content not in ("sage_reco", "sage_status", "sage_qa"):
        parts.append(content)
    if isinstance(diag, dict):
        for key in ("message", "title", "personalized_advice", "subtitle"):
            val = diag.get(key)
            if val:
                parts.append(str(val))
        cr = diag.get("chat_response")
        if isinstance(cr, dict):
            for key in ("answer", "medicine_details", "doping_check", "side_effects"):
                val = cr.get(key)
                if val:
                    parts.append(str(val))
        for sec in diag.get("sections") or []:
            if isinstance(sec, dict):
                for item in sec.get("items") or []:
                    if item:
                        parts.append(str(item))
                title = sec.get("title")
                if title:
                    parts.append(str(title))
    return _strip_html("\n".join(parts))


class LiveChatClient:
    def __init__(self, base_url: str = DEFAULT_BASE):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "routing-e2e-live/1.0"})
        self.scenario_id = ""

    def health(self) -> bool:
        try:
            return self.http.get(self.base_url, timeout=10).status_code == 200
        except requests.RequestException:
            return False

    def new_session(self, scenario_id: str = "") -> None:
        self.scenario_id = scenario_id
        headers = {"X-V2-Test-Scenario": scenario_id} if scenario_id else {}
        r = self.http.post(
            urljoin(self.base_url, "new_session"),
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()

    def chat(self, message: str, *, timeout: float = CHAT_TIMEOUT) -> tuple[int, int]:
        headers = {"X-V2-Test-Scenario": self.scenario_id} if self.scenario_id else {}
        t0 = time.perf_counter()
        r = self.http.post(
            self.base_url,
            data={"message": message},
            headers=headers,
            timeout=timeout,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        return r.status_code, elapsed

    def last_bot_message(self, *, retries: int = 8, delay: float = 0.45) -> dict:
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
                if r.ok:
                    messages = (r.json() or {}).get("messages") or []
                    for msg in reversed(messages):
                        if msg.get("type") == "bot":
                            return msg
            except requests.RequestException as exc:
                last_err = exc
            if attempt < retries - 1:
                time.sleep(delay)
        if last_err:
            raise last_err
        return {}


def load_scenarios(*, category: str | None = None) -> list[LiveScenario]:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    out: list[LiveScenario] = []
    for item in raw.get("live_scenarios") or []:
        if category and item.get("category") != category:
            continue
        turns = [
            TurnExpectation(
                user=t["user"],
                expect_route=t.get("expect_route", "any"),
                expect_render=t.get("expect_render", "any"),
                expect_kind=t.get("expect_kind"),
                must_not_kind=t.get("must_not_kind"),
                text_should_contain=list(t.get("text_should_contain") or []),
                text_must_not_contain=list(t.get("text_must_not_contain") or []),
                timeout_s=float(t.get("timeout_s", CHAT_TIMEOUT)),
            )
            for t in item.get("turns") or []
        ]
        out.append(
            LiveScenario(
                id=item["id"],
                description=item.get("description", ""),
                category=item.get("category", "general"),
                turns=turns,
            )
        )
    return out


def evaluate_turn(turn: TurnExpectation, bot: dict, status: int) -> TurnResult:
    render = _bot_render(bot)
    kind = _bot_kind(bot)
    text = _bot_text(bot)
    route = _kind_route(kind, text, render)
    intent = str(bot.get("concierge_intent") or "")
    errors: list[str] = []
    if status != 200:
        errors.append(f"HTTP {status}")
    if turn.expect_route != "any" and route != turn.expect_route:
        errors.append(f"route expected {turn.expect_route!r} got {route!r} kind={kind!r}")
    if turn.expect_render != "any" and render != turn.expect_render:
        errors.append(f"render expected {turn.expect_render!r} got {render!r}")
    if turn.expect_kind and kind != turn.expect_kind:
        errors.append(f"kind expected {turn.expect_kind!r} got {kind!r}")
    if turn.must_not_kind and kind == turn.must_not_kind:
        errors.append(f"forbidden kind {turn.must_not_kind!r}")
    for bad in turn.text_must_not_contain:
        if bad in text:
            errors.append(f"text must not contain {bad!r}")
    if turn.text_should_contain and not any(g in text for g in turn.text_should_contain):
        errors.append(
            f"text should contain one of {turn.text_should_contain!r} snippet={text[:180]!r}"
        )
    return TurnResult(
        user=turn.user,
        http_status=status,
        elapsed_ms=0,
        route=route,
        render=render,
        kind=kind,
        bot_text=text[:600],
        concierge_intent=intent,
        errors=errors,
        passed=not errors,
    )


def run_live_scenario(client: LiveChatClient, scenario: LiveScenario) -> list[TurnResult]:
    client.new_session(scenario_id=f"route-e2e-{scenario.id}")
    results: list[TurnResult] = []
    for turn in scenario.turns:
        status, elapsed = client.chat(turn.user, timeout=turn.timeout_s)
        time.sleep(0.5)
        bot = client.last_bot_message()
        tr = evaluate_turn(turn, bot, status)
        tr.elapsed_ms = elapsed
        results.append(tr)
        if not tr.passed:
            break
    return results


def write_report(
    scenarios: list[LiveScenario],
    all_results: dict[str, list[TurnResult]],
    *,
    suffix: str = "routing_e2e",
) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = REPORT_DIR / f"{ts}_local_{suffix}.json"
    md_path = REPORT_DIR / f"{ts}_local_{suffix}.md"

    passed = failed = 0
    by_category: dict[str, dict[str, int]] = {}
    lines = [
        f"# Routing E2E Live Test — {ts}",
        "",
        f"Base URL: {DEFAULT_BASE}",
        "",
    ]

    payload: dict[str, Any] = {"timestamp": ts, "scenarios": [], "summary": {}}

    for sc in scenarios:
        turns = all_results.get(sc.id, [])
        sc_pass = all(t.passed for t in turns) and len(turns) == len(sc.turns)
        if sc_pass:
            passed += 1
        else:
            failed += 1
        cat = sc.category
        by_category.setdefault(cat, {"passed": 0, "failed": 0})
        by_category[cat]["passed" if sc_pass else "failed"] += 1

        status = "PASS" if sc_pass else "FAIL"
        lines.append(f"## {sc.id} — {status} ({sc.category})")
        lines.append(f"{sc.description}")
        lines.append("")
        for t in turns:
            mark = "OK" if t.passed else "NG"
            lines.append(f"- [{mark}] `{t.user}` → route={t.route} kind={t.kind} ({t.elapsed_ms}ms)")
            if t.errors:
                lines.append(f"  - errors: {', '.join(t.errors)}")
            if not t.passed:
                lines.append(f"  - snippet: {t.bot_text[:200]}")
        lines.append("")

        payload["scenarios"].append(
            {
                "id": sc.id,
                "category": sc.category,
                "description": sc.description,
                "passed": sc_pass,
                "turns": [
                    {
                        "user": t.user,
                        "passed": t.passed,
                        "route": t.route,
                        "kind": t.kind,
                        "render": t.render,
                        "concierge_intent": t.concierge_intent,
                        "elapsed_ms": t.elapsed_ms,
                        "bot_text": t.bot_text,
                        "errors": t.errors,
                    }
                    for t in turns
                ],
            }
        )

    payload["summary"] = {
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "by_category": by_category,
    }
    lines.extend(
        [
            "## Summary",
            f"- Total: {passed + failed}",
            f"- Passed: {passed}",
            f"- Failed: {failed}",
            "",
            "### By category",
        ]
    )
    for cat, counts in sorted(by_category.items()):
        lines.append(f"- **{cat}**: {counts['passed']} pass / {counts['failed']} fail")

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def run_gpt_simulation(
    client: LiveChatClient,
    *,
    sessions: int = 3,
    max_turns: int = 6,
    openai_client: Any,
) -> list[dict[str, Any]]:
    """GPT がユーザー役で多ターン会話し、ルート誤爆を検出。"""
    personas = [
        ("tech_curious", "ITに興味のある20代。技術質問→薬の話→また技術。口語。"),
        ("athlete", "陸上競技者。のど痛・ドーピング・眠気が気になる。短文。"),
        ("elderly_family", "80代の母の服薬相談。丁寧語。副作用・飲み合わせ重視。"),
        ("boundary_mixer", "症状と技術を混ぜがち。「頭痛だけどGitHubは？」など。"),
    ]
    results: list[dict[str, Any]] = []

    for i in range(min(sessions, len(personas))):
        pid, persona = personas[i % len(personas)]
        sid = f"gpt-sim-{pid}-{i}"
        client.new_session(sid)
        history: list[dict[str, str]] = []
        opening = {
            "tech_curious": "このチャットどうやって動いてるの？",
            "athlete": "大会前なんだけどのど痛い",
            "elderly_family": "80代の母に風邪薬考えてる",
            "boundary_mixer": "頭痛するんだけど、GitLabとGitHubって何が違うの？",
        }[pid]
        user_msg = opening
        session_turns: list[dict[str, Any]] = []
        violations: list[str] = []

        for turn_idx in range(max_turns):
            status, elapsed = client.chat(user_msg)
            time.sleep(0.5)
            bot = client.last_bot_message()
            kind = _bot_kind(bot)
            text = _bot_text(bot)
            render = _bot_render(bot)
            route = _kind_route(kind, text, render)
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "bot", "content": text[:300]})

            bad = []
            if pid in ("tech_curious", "boundary_mixer") and turn_idx == 0:
                if route == "MedicineQA" or kind == "medicine_qa":
                    bad.append("turn0_should_not_be_medicine_qa")
                if "医薬品相談回答" in text:
                    bad.append("turn0_medicine_qa_title")
            if "GitHub" in user_msg or "GitLab" in user_msg or "github" in user_msg.lower():
                if route == "MedicineQA" or "医薬品相談回答" in text:
                    bad.append("tech_question_routed_to_medicine_qa")

            session_turns.append(
                {
                    "turn": turn_idx,
                    "user": user_msg,
                    "route": route,
                    "kind": kind,
                    "elapsed_ms": elapsed,
                    "violations": bad,
                    "bot_snippet": text[:200],
                }
            )
            violations.extend(bad)

            if turn_idx >= max_turns - 1:
                break

            transcript = "\n".join(
                f"{'ユーザー' if h['role']=='user' else 'ボット'}: {h['content'][:150]}"
                for h in history[-6:]
            )
            resp = openai_client.chat.completions.create(
                model=os.getenv("ROUTING_E2E_GPT_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "市販薬相談チャットのユーザー役。1文50字以内の自然な日本語。"
                            f"ペルソナ: {persona}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"会話:\n{transcript}\n\n"
                            f"ターン{turn_idx+2}/{max_turns}の次の発話をJSONのみで: "
                            '{"message":"..."}'
                        ),
                    },
                ],
                temperature=0.8,
                max_tokens=120,
            )
            raw = (resp.choices[0].message.content or "").strip()
            m = re.search(r"\{[^{}]*\"message\"\s*:\s*\"([^\"]+)\"", raw, re.DOTALL)
            user_msg = m.group(1) if m else raw[:80]

        results.append(
            {
                "persona_id": pid,
                "session_id": sid,
                "turns": session_turns,
                "violations": violations,
                "passed": not violations,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Routing E2E live test against localhost")
    parser.add_argument("--base-url", default=os.getenv("ROUTING_E2E_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--category", default="", help="Filter by category")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-gpt", action="store_true")
    parser.add_argument("--gpt-sessions", type=int, default=4)
    parser.add_argument("--gpt-turns", type=int, default=6)
    parser.add_argument("--report-suffix", default="routing_e2e")
    args = parser.parse_args()

    client = LiveChatClient(args.base_url)
    if not client.health():
        print(f"ERROR: server not reachable at {args.base_url}", file=sys.stderr)
        return 2

    scenarios = load_scenarios(category=args.category or None)
    if args.limit:
        scenarios = scenarios[: args.limit]

    all_results: dict[str, list[TurnResult]] = {}
    for sc in scenarios:
        print(f"Running {sc.id}...", flush=True)
        all_results[sc.id] = run_live_scenario(client, sc)

    json_path, md_path = write_report(scenarios, all_results, suffix=args.report_suffix)
    passed = sum(1 for sc in scenarios if all(t.passed for t in all_results[sc.id]) and len(all_results[sc.id]) == len(sc.turns))
    failed = len(scenarios) - passed
    print(f"\nYAML scenarios: {passed}/{len(scenarios)} passed, {failed} failed")
    print(f"Report: {md_path}")

    gpt_failed = 0
    if not args.skip_gpt and os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI

        oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        print(f"\nGPT simulation: {args.gpt_sessions} sessions x {args.gpt_turns} turns...")
        gpt_results = run_gpt_simulation(
            client,
            sessions=args.gpt_sessions,
            max_turns=args.gpt_turns,
            openai_client=oai,
        )
        gpt_pass = sum(1 for r in gpt_results if r["passed"])
        gpt_failed = len(gpt_results) - gpt_pass
        gpt_path = REPORT_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_local_{args.report_suffix}_gpt.json"
        gpt_path.write_text(json.dumps(gpt_results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"GPT simulation: {gpt_pass}/{len(gpt_results)} passed")
        print(f"GPT report: {gpt_path}")
        for r in gpt_results:
            if r["violations"]:
                print(f"  - {r['persona_id']}: {r['violations']}")

    return 1 if (failed or gpt_failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
