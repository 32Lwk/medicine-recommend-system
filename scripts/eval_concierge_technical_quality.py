#!/usr/bin/env python3
"""Concierge 技術回答品質 contract eval（LLM なし）。

Usage:
  .venv/bin/python scripts/eval_concierge_technical_quality.py
  .venv/bin/python scripts/eval_concierge_technical_quality.py --min-pass-pct 90
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_technical_quality.yaml"


def _load_fixture(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _build_reference(message: str, *, deep: bool) -> str:
    from src.content.concierge_tech_reference import augment_architecture_reference

    base = "【エージェント構成（参照）】\n- TriageAgent: 振り分け"
    return augment_architecture_reference(base, deep=deep, user_text=message)


def _evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    forbidden_patterns: List[str],
) -> Dict[str, Any]:
    from src.content.concierge_tech_reference import wants_technical_deep_dive
    from src.services.concierge_intent import probe_meta_concierge_intent

    message = str(scenario.get("message") or "").strip()
    history = scenario.get("history")
    sid = scenario.get("id")
    failures: List[str] = []

    expected_intent_raw = scenario.get("expected_intent")
    expected_intent: Optional[str]
    if expected_intent_raw in (None, "null", ""):
        expected_intent = None
    else:
        expected_intent = str(expected_intent_raw)

    actual_intent = probe_meta_concierge_intent(message)
    intent_pass = actual_intent == expected_intent
    if not intent_pass:
        failures.append(f"intent: expected={expected_intent!r} actual={actual_intent!r}")

    if scenario.get("expect_deep_dive") is not None:
        deep_actual = wants_technical_deep_dive(message, history)
        if deep_actual is not scenario["expect_deep_dive"]:
            failures.append(
                f"deep_dive: expected={scenario['expect_deep_dive']} actual={deep_actual}"
            )

    doc_intent = scenario.get("doc_intent")
    if doc_intent:
        from src.content.concierge_docs import load_concierge_doc

        title, body = load_concierge_doc(str(doc_intent))
        if not title or not body.strip():
            failures.append(f"doc_missing: {doc_intent}")

    if not scenario.get("skip_reference"):
        deep = bool(scenario.get("expect_deep_dive"))
        ref = _build_reference(message, deep=deep)
        for needle in scenario.get("reference_must_contain") or []:
            if needle not in ref:
                failures.append(f"missing_ref: {needle!r}")
        # env 名禁止は runtime ブロックのみ（ops SSOT 本文は除外）
        runtime_part = ref.split("【公開デプロイ情報", 1)[-1] if "【公開デプロイ情報" in ref else ""
        for pattern in forbidden_patterns:
            if pattern in runtime_part:
                failures.append(f"forbidden_runtime: {pattern!r}")

    return {
        "id": sid,
        "message": message,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "pass": not failures,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge technical quality contract eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-pass-pct", type=float, default=90.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    doc = _load_fixture(args.fixture)
    forbidden = [str(x) for x in (doc.get("reference_forbidden_patterns") or [])]
    results = [
        _evaluate_scenario(s, forbidden_patterns=forbidden)
        for s in (doc.get("scenarios") or [])
    ]

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    pct = (100.0 * passed / total) if total else 0.0
    summary = {
        "eval": "concierge_technical_quality",
        "fixture": str(args.fixture.relative_to(ROOT)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "pass_pct": round(pct, 1),
        "min_pass_pct": args.min_pass_pct,
        "go": pct >= args.min_pass_pct,
        "results": results,
    }

    out_path = args.output or (
        ROOT / "log/analysis" / f"concierge_technical_quality_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Quality contract: {passed}/{total} ({pct:.1f}%) — {'GO' if summary['go'] else 'NO-GO'}")
    if not summary["go"]:
        for r in results:
            if not r["pass"]:
                print(f"  FAIL {r['id']}: {', '.join(r['failures'])}")
        return 1
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
