"""
localhost 統合テスト — 競技・推奨文脈の意図整合。

Usage:
  py -3.13 -m pytest tests/routing/test_medicine_context_live_integration.py -v -s
  py -3.13 scripts/test_medicine_context_live.py --base-url http://127.0.0.1:5000/
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import pytest
import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "medicine_context_live_scenarios.yaml"
REPORT_DIR = PROJECT_ROOT / "log" / "analysis"
DEFAULT_BASE = "http://127.0.0.1:5000/"
CHAT_TIMEOUT = 180.0

HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class TurnExpectation:
    user: str
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
    turns: list[TurnExpectation]


@dataclass
class TurnResult:
    user: str
    http_status: int
    elapsed_ms: int
    render: str = ""
    kind: str = ""
    bot_text: str = ""
    errors: list[str] = field(default_factory=list)
    passed: bool = True


def _load_scenarios() -> list[LiveScenario]:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    out: list[LiveScenario] = []
    for item in raw.get("live_scenarios") or []:
        turns = [
            TurnExpectation(
                user=t["user"],
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
                turns=turns,
            )
        )
    return out


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
        for key in (
            "message",
            "title",
            "personalized_advice",
            "subtitle",
        ):
            val = diag.get(key)
            if val:
                parts.append(str(val))
        cr = diag.get("chat_response")
        if isinstance(cr, dict):
            for key in (
                "answer",
                "medicine_details",
                "doping_check",
                "side_effects",
                "interactions",
                "consultation_advice",
            ):
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
        for med in diag.get("recommended_medicines") or []:
            if isinstance(med, dict) and med.get("product_name"):
                parts.append(str(med["product_name"]))
    return _strip_html("\n".join(parts))


class LiveChatClient:
    def __init__(self, base_url: str = DEFAULT_BASE):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.http = requests.Session()
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

    def last_bot_message(self, *, retries: int = 8, delay: float = 0.4) -> dict:
        for attempt in range(retries):
            r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
            if r.ok:
                messages = (r.json() or {}).get("messages") or []
                for msg in reversed(messages):
                    if msg.get("type") == "bot":
                        return msg
            if attempt < retries - 1:
                time.sleep(delay)
        return {}


def run_live_scenario(client: LiveChatClient, scenario: LiveScenario) -> list[TurnResult]:
    client.new_session(scenario_id=f"medctx-{scenario.id}")
    results: list[TurnResult] = []
    for turn in scenario.turns:
        status, elapsed = client.chat(turn.user, timeout=turn.timeout_s)
        time.sleep(0.5)
        bot = client.last_bot_message()
        render = _bot_render(bot)
        kind = _bot_kind(bot)
        text = _bot_text(bot)
        errors: list[str] = []
        if status != 200:
            errors.append(f"HTTP {status}")
        if turn.expect_render != "any" and render != turn.expect_render:
            errors.append(f"render expected {turn.expect_render!r} got {render!r}")
        if turn.expect_kind and kind != turn.expect_kind:
            errors.append(f"kind expected {turn.expect_kind!r} got {kind!r}")
        if turn.must_not_kind and kind == turn.must_not_kind:
            errors.append(f"forbidden kind {turn.must_not_kind!r}")
        for bad in turn.text_must_not_contain:
            if bad in text:
                errors.append(f"text must not contain {bad!r}")
        if turn.text_should_contain:
            if not any(good in text for good in turn.text_should_contain):
                errors.append(
                    f"text should contain one of {turn.text_should_contain!r} "
                    f"snippet={text[:200]!r}"
                )
        results.append(
            TurnResult(
                user=turn.user,
                http_status=status,
                elapsed_ms=elapsed,
                render=render,
                kind=kind,
                bot_text=text[:500],
                errors=errors,
                passed=not errors,
            )
        )
        if errors:
            break
    return results


def write_report(scenarios: list[LiveScenario], all_results: dict[str, list[TurnResult]]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    path = REPORT_DIR / f"{ts}_medicine_context_live.json"
    payload: dict[str, Any] = {
        "timestamp": ts,
        "scenarios": [],
        "summary": {"total": 0, "passed": 0, "failed": 0},
    }
    for sc in scenarios:
        turns = all_results.get(sc.id, [])
        sc_pass = all(t.passed for t in turns) and len(turns) == len(sc.turns)
        payload["scenarios"].append(
            {
                "id": sc.id,
                "description": sc.description,
                "passed": sc_pass,
                "turns": [
                    {
                        "user": t.user,
                        "passed": t.passed,
                        "http_status": t.http_status,
                        "elapsed_ms": t.elapsed_ms,
                        "render": t.render,
                        "kind": t.kind,
                        "bot_text": t.bot_text,
                        "errors": t.errors,
                    }
                    for t in turns
                ],
            }
        )
        payload["summary"]["total"] += 1
        if sc_pass:
            payload["summary"]["passed"] += 1
        else:
            payload["summary"]["failed"] += 1
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def live_base_url() -> str:
    import os

    return os.getenv("MEDICINE_CONTEXT_TEST_BASE_URL", DEFAULT_BASE)


@pytest.fixture(scope="module")
def live_client(live_base_url: str) -> LiveChatClient:
    client = LiveChatClient(live_base_url)
    if not client.health():
        pytest.skip(f"localhost not reachable: {live_base_url}")
    return client


@pytest.mark.live
@pytest.mark.parametrize(
    "scenario",
    _load_scenarios(),
    ids=[s.id for s in _load_scenarios()],
)
def test_medicine_context_live_scenario(live_client: LiveChatClient, scenario: LiveScenario):
    results = run_live_scenario(live_client, scenario)
    failures = []
    for tr in results:
        if not tr.passed:
            failures.append(
                f"user={tr.user!r} errors={tr.errors} render={tr.render} kind={tr.kind} "
                f"text={tr.bot_text[:120]!r}"
            )
    if len(results) < len(scenario.turns):
        failures.append(f"stopped early at turn {len(results)}/{len(scenario.turns)}")
    assert not failures, "\n".join(failures)


def run_all_and_report(base_url: str = DEFAULT_BASE) -> int:
    """CLI エントリ。失敗シナリオ数を返す。"""
    scenarios = _load_scenarios()
    client = LiveChatClient(base_url)
    if not client.health():
        print(f"ERROR: cannot reach {base_url}")
        return 1
    all_results: dict[str, list[TurnResult]] = {}
    failed = 0
    for sc in scenarios:
        print(f"\n=== {sc.id}: {sc.description} ===")
        results = run_live_scenario(client, sc)
        all_results[sc.id] = results
        ok = all(t.passed for t in results) and len(results) == len(sc.turns)
        for tr in results:
            status = "PASS" if tr.passed else "FAIL"
            print(f"  [{status}] {tr.user[:40]!r} render={tr.render} kind={tr.kind} {tr.elapsed_ms}ms")
            for e in tr.errors:
                print(f"         ! {e}")
        if not ok:
            failed += 1
    report_path = write_report(scenarios, all_results)
    print(f"\nReport: {report_path}")
    print(f"Summary: {len(scenarios) - failed}/{len(scenarios)} scenarios passed")
    return failed


if __name__ == "__main__":
    import sys

    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    raise SystemExit(run_all_and_report(base))
