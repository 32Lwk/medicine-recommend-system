#!/usr/bin/env python3
"""Concierge Meta KB ライブ LLM 品質 eval。

Usage:
  .venv/bin/python scripts/eval_concierge_technical_quality_live.py
  .venv/bin/python scripts/eval_concierge_technical_quality_live.py --judge --max-scenarios 10
  .venv/bin/python scripts/eval_concierge_technical_quality_live.py --dry-run

OPENAI_API_KEY 必須（--dry-run 除く。.env から load_dotenv）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

# ローカル eval では Local RAG を既定（Bedrock 資格情報不要・低レイテンシ）
os.environ.setdefault("CONCIERGE_RAG_PROVIDER", "local")

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_technical_quality_live.yaml"


def _load_fixture(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _generate_answer(
    client: Any,
    scenario: Dict[str, Any],
    *,
    intent: str,
) -> tuple[str, float, bool]:
    """回答生成 + レイテンシ ms。本番と同じ build_concierge_payload 経路。"""
    from src.agents.concierge_agent import build_concierge_payload

    message = str(scenario.get("message") or "").strip()
    history = scenario.get("history") or []
    start = time.time()

    payload = build_concierge_payload(
        intent,  # type: ignore[arg-type]
        message,
        client,
        history=history,
    )
    text = _payload_plain_text(payload)
    llm_used = bool(payload.get("llm_used"))
    latency_ms = round((time.time() - start) * 1000, 1)
    return text, latency_ms, llm_used


def _payload_plain_text(payload: Dict[str, Any]) -> str:
    """status_card / text いずれの payload からもプレーンテキストを抽出。"""
    plain = str(payload.get("content_plain") or "").strip()
    if plain:
        return plain
    diag = payload.get("sage_diagnosis")
    if isinstance(diag, dict):
        msg = str(diag.get("message") or "").strip()
        sections = diag.get("sections") or []
        if not msg and sections:
            parts: List[str] = []
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                title = str(sec.get("title") or "").strip()
                items = sec.get("items") or []
                if title:
                    parts.append(title)
                for item in items:
                    if str(item).strip():
                        parts.append(str(item).strip())
            msg = "\n".join(parts).strip()
        if msg:
            return msg
    content = str(payload.get("content") or "").strip()
    if not content:
        return ""
    if "chat-status-card" in content:
        from src.agents.concierge_agent import html_to_plain_from_card

        plain = html_to_plain_from_card(content)
        if plain.strip():
            return plain
    return content


def _llm_judge_answer(
    client: Any,
    *,
    question: str,
    answer: str,
    intent: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from src.services.concierge_live_judge import llm_judge_concierge_answer

    return llm_judge_concierge_answer(
        client,
        question=question,
        answer=answer,
        intent=intent,
        history=history,
    )


def _evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    client: Any,
    forbidden: List[str],
    tier: str,
) -> Dict[str, Any]:
    sid = str(scenario.get("id") or "")
    message = str(scenario.get("message") or "").strip()
    failures: List[str] = []
    answer = ""
    latency_ms = 0.0
    llm_used = False
    judge: Optional[Dict[str, Any]] = None

    if scenario.get("skip_answer"):
        if scenario.get("expect_route"):
            from src.services.medicine_qa_eligibility import (
                MedicineQaRoute,
                resolve_medicine_qa_route,
            )

            route = resolve_medicine_qa_route(
                message,
                conversation_history=scenario.get("history"),
                client=client,
            )
            expected = str(scenario["expect_route"])
            if expected == "medicine_qa":
                ok = route.route == MedicineQaRoute.MEDICINE_QA
            else:
                ok = route.route.value == expected
            if not ok:
                failures.append(f"route: expected={expected} actual={route.route.value}")
        if scenario.get("expect_clarification"):
            from src.services.concierge_intent import build_ambiguous_meta_clarification

            clar = build_ambiguous_meta_clarification(message)
            if not clar:
                failures.append("clarification: expected non-empty")
        return {
            "id": sid,
            "message": message,
            "pass": not failures,
            "failures": failures,
            "latency_ms": 0,
            "answer_preview": "",
        }

    intent_raw = scenario.get("intent")
    intent = str(intent_raw) if intent_raw not in (None, "null", "") else "architecture"

    from src.services.concierge_intent import probe_meta_concierge_intent

    probed = probe_meta_concierge_intent(message)
    if intent_raw not in (None, "null", "") and probed and probed != intent:
        # follow-up は probe が architecture に寄ることがある — history ありは許容
        if not scenario.get("history"):
            failures.append(f"intent_probe: expected={intent} probed={probed}")

    try:
        answer, latency_ms, llm_used = _generate_answer(client, scenario, intent=intent)
    except Exception as exc:
        failures.append(f"generate_error: {exc}")
        return {
            "id": sid,
            "message": message,
            "intent": intent,
            "pass": False,
            "failures": failures,
            "latency_ms": 0,
            "answer_preview": "",
        }

    min_chars = int(scenario.get("min_chars") or 30)
    if len((answer or "").strip()) < min_chars:
        failures.append(f"too_short: {len((answer or '').strip())} < {min_chars}")

    for pattern in forbidden:
        if pattern in answer:
            failures.append(f"forbidden: {pattern!r}")

    for pattern in scenario.get("must_not_contain") or []:
        if pattern in answer:
            failures.append(f"must_not: {pattern!r}")

    must_any = [str(x) for x in (scenario.get("must_contain_any") or [])]
    if must_any and not any(term in answer for term in must_any):
        failures.append(f"must_contain_any: {must_any}")

    rule_pass = not failures
    judge: Optional[Dict[str, Any]] = None
    judge_recovered = False

    from src.services.concierge_live_judge import judge_passes

    should_judge = False
    if tier == "judge-pass" and rule_pass and answer.strip():
        should_judge = True
    elif tier == "judge-failures" and not rule_pass and answer.strip():
        should_judge = True
    elif tier == "judge-all" and answer.strip():
        should_judge = True

    if should_judge:
        judge = _llm_judge_answer(
            client,
            question=message,
            answer=answer,
            intent=intent,
            history=scenario.get("history"),
        )
        if tier == "judge-failures" and judge_passes(judge or {}):
            judge_recovered = True
        elif tier in ("judge-pass", "judge-all") and not judge_passes(judge or {}):
            failures.append(f"judge: {(judge or {}).get('reason', judge)}")

    hard_failures = [
        f
        for f in failures
        if f.startswith(("forbidden:", "must_not:", "generate_error:", "too_short:"))
    ]
    final_pass = not failures
    if tier == "judge-failures" and judge_recovered and not hard_failures:
        final_pass = True

    return {
        "id": sid,
        "message": message,
        "intent": intent,
        "pass": final_pass,
        "rule_pass": rule_pass,
        "judge_recovered": judge_recovered,
        "failures": failures,
        "latency_ms": latency_ms,
        "llm_used": llm_used,
        "judge": judge,
        "answer_preview": (answer or "")[:400],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge live LLM quality eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-pass-pct", type=float, default=85.0)
    parser.add_argument(
        "--tier",
        choices=("rule", "judge-pass", "judge-failures", "judge-all"),
        default="rule",
        help="L3 tier: rule | judge-pass (L3c strict) | judge-failures (L3b rescue) | judge-all",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Deprecated alias for --tier judge-pass",
    )
    parser.add_argument("--max-scenarios", type=int, default=0, help="Limit scenarios (cost control)")
    parser.add_argument("--dry-run", action="store_true", help="List scenarios only")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    doc = _load_fixture(args.fixture)
    scenarios = list(doc.get("scenarios") or [])
    if args.max_scenarios > 0:
        scenarios = scenarios[: args.max_scenarios]

    tier = args.tier
    if args.judge and tier == "rule":
        tier = "judge-pass"

    if args.dry_run:
        print(f"Scenarios: {len(scenarios)}")
        for s in scenarios:
            print(f"  - {s.get('id')}: {s.get('message', '')[:50]}")
        return 0

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY unset — skip live eval", file=sys.stderr)
        return 2

    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    forbidden = [str(x) for x in (doc.get("forbidden_patterns") or [])]

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    for scenario in scenarios:
        row = _evaluate_scenario(
            scenario,
            client=client,
            forbidden=forbidden,
            tier=tier,
        )
        results.append(row)
        if row.get("latency_ms"):
            latencies.append(float(row["latency_ms"]))
        mark = "OK" if row["pass"] else "NG"
        print(f"  [{mark}] {row['id']}: {row.get('latency_ms', 0):.0f}ms")
        if not row["pass"]:
            print(f"       {', '.join(row.get('failures') or [])}")

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    pct = (100.0 * passed / total) if total else 0.0
    p95 = 0.0
    if latencies:
        sorted_lat = sorted(latencies)
        p95 = sorted_lat[int(round(0.95 * (len(sorted_lat) - 1)))]

    summary = {
        "eval": "concierge_technical_quality_live",
        "fixture": str(args.fixture.resolve().relative_to(ROOT.resolve())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "pass_pct": round(pct, 1),
        "min_pass_pct": args.min_pass_pct,
        "tier": tier,
        "judge_enabled": tier != "rule",
        "latency_ms_p95": round(p95, 1),
        "latency_ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "go": pct >= args.min_pass_pct,
        "results": results,
    }

    out_path = args.output or (
        ROOT / "log/analysis" / f"concierge_technical_quality_live_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Live quality: {passed}/{total} ({pct:.1f}%) — "
        f"{'GO' if summary['go'] else 'NO-GO'} "
        f"(P95 {p95:.0f}ms)"
    )
    print(f"Report: {out_path}")
    return 0 if summary["go"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
