#!/usr/bin/env python3
"""Concierge boundary eval — faithfulness / sanitize（LLM なし）。

Usage:
  .venv/bin/python scripts/eval_concierge_boundary.py
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

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_boundary.yaml"


def _load_fixture(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.concierge_output_sanitize import (
        apply_concierge_faithfulness_guard,
        sanitize_concierge_meta_output,
    )

    raw = str(scenario.get("input") or "")
    intent = str(scenario.get("intent") or "")
    out = apply_concierge_faithfulness_guard(
        sanitize_concierge_meta_output(raw, intent=intent),
        intent=intent,
    )
    failures: List[str] = []
    for token in scenario.get("must_not_contain") or []:
        if str(token) in out:
            failures.append(f"forbidden:{token!r}")
    must_any = [str(x) for x in (scenario.get("must_contain_any") or [])]
    if must_any and not any(t in out for t in must_any):
        failures.append(f"missing_any:{must_any!r}")
    return {
        "id": scenario.get("id"),
        "intent": intent,
        "output_preview": out[:200],
        "pass": not failures,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge boundary eval")
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
        "eval": "concierge_boundary",
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
        ROOT / "log/analysis" / f"concierge_boundary_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Boundary: {passed}/{total} ({pct:.1f}%) — {'GO' if summary['go'] else 'NO-GO'}")
    if not summary["go"]:
        for r in results:
            if not r["pass"]:
                print(f"  FAIL {r['id']}: {', '.join(r['failures'])}")
        return 1
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
