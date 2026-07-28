#!/usr/bin/env python3
"""Concierge LINE smoke contract eval（LLM/HTTP なし）。

Usage:
  .venv/bin/python scripts/eval_concierge_line_smoke.py
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

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_line_smoke.yaml"


def _load_fixture(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.concierge_channel import (
        is_concierge_line_channel,
        line_architecture_follow_up_hint,
    )
    from src.services.concierge_intent import probe_meta_concierge_intent

    message = str(scenario.get("message") or "").strip()
    session_id = str(scenario.get("session_id") or "")
    failures: List[str] = []

    expected_raw = scenario.get("expected_intent")
    expected: Optional[str]
    if expected_raw in (None, "null", ""):
        expected = None
    else:
        expected = str(expected_raw)
    actual = probe_meta_concierge_intent(message)
    if actual != expected:
        failures.append(f"intent: expected={expected!r} actual={actual!r}")

    if scenario.get("expect_line_channel"):
        if not is_concierge_line_channel(session_id):
            failures.append("line_channel: expected True")

    if scenario.get("expect_follow_up_hint"):
        hint = line_architecture_follow_up_hint(deep=False)
        if not hint:
            failures.append("follow_up_hint: missing")

    return {
        "id": scenario.get("id"),
        "message": message,
        "pass": not failures,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge LINE smoke contract eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-pass-pct", type=float, default=100.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    doc = _load_fixture(args.fixture)
    results = [_evaluate_scenario(s) for s in (doc.get("scenarios") or [])]
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    pct = (100.0 * passed / total) if total else 0.0
    summary = {
        "eval": "concierge_line_smoke",
        "fixture": str(args.fixture.relative_to(ROOT)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "pass_pct": round(pct, 1),
        "go": pct >= args.min_pass_pct,
        "results": results,
    }

    out_path = args.output or (
        ROOT / "log/analysis" / f"concierge_line_smoke_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"LINE smoke: {passed}/{total} ({pct:.1f}%) — {'GO' if summary['go'] else 'NO-GO'}")
    if not summary["go"]:
        for r in results:
            if not r["pass"]:
                print(f"  FAIL {r['id']}: {', '.join(r['failures'])}")
        return 1
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
