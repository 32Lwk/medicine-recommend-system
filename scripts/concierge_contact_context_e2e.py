#!/usr/bin/env python3
"""Concierge 連絡先・案内カード文脈 E2E（localhost :5000）。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCENARIOS_PATH = PROJECT_ROOT / "tests" / "fixtures" / "concierge_contact_context_e2e.yaml"
DEFAULT_BASE = os.getenv("V2_TEST_BASE_URL", "http://127.0.0.1:5000/")
HTML_TAG_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r"""href=["']([^"']+)["']""", re.I)


@dataclass
class TurnResult:
    turn_index: int
    user_message: str
    http_status: int
    elapsed_ms: int
    diagnosis_kind: Optional[str] = None
    response_text: str = ""
    response_full: str = ""
    has_contact_sections: bool = False
    error: str = ""


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    session_id: str
    turns: list[TurnResult] = field(default_factory=list)
    auto_pass: bool = False
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class E2EClient:
    def __init__(self, base_url: str, scenario_id: str = "") -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "local-v2-chat-test/2.0"})
        self._scenario_id = scenario_id
        self._sid: Optional[str] = None

    def new_session(self) -> str:
        r = self.http.post(
            urljoin(self.base_url, "new_session"),
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self._sid = str(data.get("session_id") or self.http.cookies.get("sid") or "")
        return self._sid

    def _headers(self) -> dict[str, str]:
        if self._scenario_id:
            return {"X-V2-Test-Scenario": self._scenario_id}
        return {}

    def chat(self, message: str) -> tuple[dict[str, Any], list[dict]]:
        t0 = time.perf_counter()
        r = self.http.post(
            self.base_url,
            data={"message": message},
            headers=self._headers(),
            timeout=120,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        body: dict[str, Any] = {}
        try:
            body = r.json() if r.content else {}
        except Exception:
            body = {"error": r.text[:500]}
        body["_http_status"] = r.status_code
        body["_elapsed_ms"] = elapsed
        return body, self._session_messages()

    def _session_messages(self) -> list[dict]:
        for _ in range(5):
            r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
            if r.ok:
                msgs = list((r.json() or {}).get("messages") or [])
                if msgs:
                    return msgs
            time.sleep(0.35)
        return []


def _strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def _bot_payload(msg: dict[str, Any]) -> tuple[str, str, bool]:
    diag = msg.get("diagnosis") or {}
    kind = str(diag.get("kind") or "")
    if not kind and msg.get("concierge_intent"):
        kind = f"concierge_{msg.get('concierge_intent')}"

    parts: list[str] = []
    for key in ("title", "subtitle", "message"):
        val = diag.get(key)
        if val:
            parts.append(_strip_html(str(val)))
    has_contact = False
    for sec in diag.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        html = str(sec.get("html") or "")
        items = sec.get("items") or []
        parts.append(_strip_html(html))
        parts.extend(_strip_html(str(i)) for i in items)
        for href in _HREF_RE.findall(html):
            parts.append(href)
        blob = html + " ".join(str(i) for i in items)
        if "mailto:" in blob or "forms.gle" in blob or "不具合報告" in blob:
            has_contact = True
    full = "\n".join(p for p in parts if p)
    return kind, full, has_contact


def _last_bot(messages: list[dict]) -> tuple[str, str, bool]:
    for msg in reversed(messages):
        if msg.get("type") == "bot":
            return _bot_payload(msg)
    return "", "", False


def _gpt_user_reply(history: list[tuple[str, str]], *, goal: str, system: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    lines = [f"{role}: {text[:200]}" for role, text in history[-6:]]
    prompt = (
        f"{system}\n\n目標: {goal}\n会話:\n" + "\n".join(lines) + "\n\n次のユーザー発話を1文だけ:"
    )
    resp = client.chat.completions.create(
        model=os.getenv("V2_TEST_GPT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=80,
    )
    return (resp.choices[0].message.content or "連絡先教えて").strip().split("\n")[0]


def _evaluate(spec: dict[str, Any], turns: list[TurnResult]) -> tuple[bool, list[str], list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    expect = spec.get("expect") or {}
    last = turns[-1] if turns else None
    if not last:
        return False, notes, ["no_turns"]

    if expect.get("min_turns") and len(turns) < int(expect["min_turns"]):
        failures.append("min_turns_not_met")

    if expect.get("diagnosis_kind") and (last.diagnosis_kind or "") != str(expect["diagnosis_kind"]):
        failures.append(f"kind_mismatch:{last.diagnosis_kind}")

    if expect.get("must_not_kind"):
        bad = str(expect["must_not_kind"])
        if bad in (last.diagnosis_kind or ""):
            failures.append(f"must_not_kind:{bad}")

    if expect.get("has_contact_sections"):
        if not any(t.has_contact_sections for t in turns):
            failures.append("missing_contact_sections")

    if expect.get("last_has_contact_or_concierge"):
        if not (last.has_contact_sections or "operator" in (last.diagnosis_kind or "")):
            if not any("operator" in (t.diagnosis_kind or "") for t in turns):
                failures.append("last_not_concierge_contact")

    text = last.response_full or last.response_text
    for kw in expect.get("context_keywords") or []:
        if kw.lower() not in text.lower():
            failures.append(f"missing_kw:{kw}")
        else:
            notes.append(f"kw:{kw}")

    for bad in expect.get("must_not_contain") or []:
        if str(bad) in text:
            failures.append(f"must_not_contain:{bad}")

    return len(failures) == 0, notes, failures


def _run_scenario(spec: dict[str, Any], *, base_url: str, use_gpt: bool) -> ScenarioResult:
    client = E2EClient(base_url, scenario_id=str(spec["id"]))
    sid = client.new_session()
    turns: list[TurnResult] = []
    history: list[tuple[str, str]] = []
    all_msgs = list(spec.get("setup") or [])
    if spec.get("input"):
        all_msgs.append(str(spec["input"]).strip())

    for idx, msg in enumerate(all_msgs):
        body, messages = client.chat(msg)
        kind, full, has_contact = _last_bot(messages)
        turns.append(
            TurnResult(
                idx, msg, int(body.get("_http_status", 0)), int(body.get("_elapsed_ms", 0)),
                kind or None, full[:300], full, has_contact, str(body.get("error") or ""),
            )
        )
        history.extend([("user", msg), ("bot", full)])
        time.sleep(0.3)

    for d in range(int(spec.get("dynamic_turns") or 0)):
        msg = (
            _gpt_user_reply(history, goal=str(spec.get("dynamic_goal") or ""), system=str(spec.get("persona_system") or ""))
            if use_gpt else "連絡先教えて"
        )
        body, messages = client.chat(msg)
        kind, full, has_contact = _last_bot(messages)
        turns.append(
            TurnResult(
                len(all_msgs) + d, msg, int(body.get("_http_status", 0)), int(body.get("_elapsed_ms", 0)),
                kind or None, full[:300], full, has_contact,
            )
        )
        history.extend([("user", msg), ("bot", full)])
        time.sleep(0.3)

    ok, notes, failures = _evaluate(spec, turns)
    return ScenarioResult(str(spec["id"]), str(spec.get("category") or ""), sid, turns, ok, failures, notes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--use-gpt-user", action="store_true")
    parser.add_argument("--report-suffix", default="contact")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    try:
        requests.get(args.base_url.rstrip("/") + "/health", timeout=30).raise_for_status()
    except Exception:
        print(f"ERROR: server not reachable at {args.base_url}", file=sys.stderr)
        return 2

    scenarios = yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8")).get("scenarios") or []
    if args.limit:
        scenarios = scenarios[: args.limit]
    if args.use_gpt_user and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    results = []
    for i, spec in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] {spec['id']} ...", flush=True)
        results.append(_run_scenario(spec, base_url=args.base_url, use_gpt=args.use_gpt_user))

    passed = sum(1 for r in results if r.auto_pass)
    date_slug = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    out_dir = PROJECT_ROOT / "log" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{date_slug}_concierge_contact_context_e2e_{args.report_suffix}.md"
    json_path = out_dir / f"{date_slug}_concierge_contact_context_e2e_{args.report_suffix}.json"
    json_path.write_text(
        json.dumps({"passed": passed, "total": len(results), "results": [asdict(r) for r in results]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [f"# Concierge Contact Context E2E\n\nPassed: **{passed}/{len(results)}**\n"]
    for r in results:
        last = r.turns[-1] if r.turns else None
        lines.append(
            f"- {r.scenario_id}: {'OK' if r.auto_pass else 'NG'} "
            f"({', '.join(r.failures) or 'ok'}) kind={getattr(last, 'diagnosis_kind', '-')}"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nDone: {passed}/{len(results)} -> {md_path}")
    return 0 if passed >= len(results) * 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
