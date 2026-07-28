#!/usr/bin/env python3
"""Concierge intent routing eval — probe_meta + Medicine QA 境界。

Usage:
  .venv/bin/python scripts/eval_concierge_intent_routing.py
  .venv/bin/python scripts/eval_concierge_intent_routing.py --min-pass-pct 92
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_intent_routing.yaml"


def _load_fixture(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.concierge_intent import probe_meta_concierge_intent

    query = str(scenario.get("query") or "").strip()
    expected_raw = scenario.get("expected_intent")
    expected = None if expected_raw in (None, "null", "") else str(expected_raw)
    actual = probe_meta_concierge_intent(query)
    passed = actual == expected
    return {
        "id": scenario.get("id"),
        "query": query,
        "expected_intent": expected,
        "actual_intent": actual,
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge intent routing eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-pass-pct", type=float, default=92.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    doc = _load_fixture(args.fixture)
    results: List[Dict[str, Any]] = []
    for scenario in doc.get("scenarios") or []:
        results.append(_evaluate_scenario(scenario))

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    pct = (100.0 * passed / total) if total else 0.0
    summary = {
        "eval": "concierge_intent_routing",
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
        ROOT / "log/analysis" / f"concierge_intent_routing_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Intent routing: {passed}/{total} ({pct:.1f}%) — {'GO' if summary['go'] else 'NO-GO'}")
    if not summary["go"]:
        for r in results:
            if not r["pass"]:
                print(f"  FAIL {r['id']}: expected={r['expected_intent']!r} actual={r['actual_intent']!r}")
        return 1
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
