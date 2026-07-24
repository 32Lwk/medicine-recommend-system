#!/usr/bin/env python3
"""Medicine Managed KB retrieve 評価（baseline / Phase 1 再計測）。

Usage:
  AWS_PROFILE=admin .venv/bin/python scripts/eval_medicine_kb.py
  AWS_PROFILE=admin .venv/bin/python scripts/eval_medicine_kb.py --output log/analysis/medicine_kb_baseline_20260724.json
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

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _load_fixture(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    # minimal fallback without PyYAML
    raise SystemExit("PyYAML required: pip install pyyaml")


def _uri_matches_prefix(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    # s3://bucket/medicine/data/... or https://...amazonaws.com/medicine/data/...
    needle = prefix.strip("/")
    return needle in uri.replace("\\", "/")


def _evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    kb_id: str,
    search_mode: str,
    region: str,
    top_k: int,
) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import retrieve_kb_context

    query = str(scenario.get("query") or "").strip()
    min_score = float(scenario.get("min_score") or 0.5)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")

    result = retrieve_kb_context(
        query,
        kb_id=kb_id,
        cache_namespace="medicine_eval",
        top_k=top_k,
        use_cache=False,
        search_mode=search_mode,
    )

    scores: List[float] = []
    for src in result.get("sources") or []:
        sc = src.get("score")
        if sc is not None:
            try:
                scores.append(float(sc))
            except (TypeError, ValueError):
                pass
    top_score = max(scores) if scores else 0.0
    source_uris: List[str] = list(result.get("source_uris") or [])
    prefix_hit = any(_uri_matches_prefix(u, expected_prefix) for u in source_uris)
    score_pass = top_score >= min_score
    pass_all = score_pass and (prefix_hit if expected_prefix else True)

    return {
        "id": scenario.get("id"),
        "category": scenario.get("category"),
        "query": query,
        "min_score": min_score,
        "expected_source_prefix": expected_prefix,
        "chunk_count": int(result.get("chunk_count") or 0),
        "top_score": round(top_score, 4),
        "source_uris": source_uris[:5],
        "kb_retrieve_ms": result.get("kb_retrieve_ms"),
        "score_pass": score_pass,
        "prefix_pass": prefix_hit,
        "pass": pass_all,
        "provider": result.get("provider"),
        "dropped_low_score": result.get("dropped_low_score"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Medicine KB retrieve against fixture")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/medicine_kb_eval.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output path (default: log/analysis/medicine_kb_baseline_YYYYMMDD.json)",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--phase",
        default="phase2_kb",
        help="Report label (e.g. phase0_baseline, phase2_kb)",
    )
    args = parser.parse_args()

    if yaml is None:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
        import yaml as yaml_mod  # noqa: F401

    fixture = _load_fixture(args.fixture)
    kb_id = str(fixture.get("kb_id") or "30BCEJCJHA")
    search_mode = str(fixture.get("search_mode") or "managed")
    region = str(fixture.get("region") or "ap-northeast-1")
    scenarios = fixture.get("scenarios") or []

    rows: List[Dict[str, Any]] = []
    for sc in scenarios:
        rows.append(
            _evaluate_scenario(
                sc,
                kb_id=kb_id,
                search_mode=search_mode,
                region=region,
                top_k=args.top_k,
            )
        )

    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    score_only = sum(1 for r in rows if r.get("score_pass"))

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "kb_id": kb_id,
        "search_mode": search_mode,
        "region": region,
        "fixture": str(args.fixture.relative_to(ROOT)),
        "summary": {
            "total": total,
            "pass_all": passed,
            "pass_all_pct": round(100.0 * passed / total, 1) if total else 0.0,
            "score_pass": score_only,
            "score_pass_pct": round(100.0 * score_only / total, 1) if total else 0.0,
            "target_pass_pct": 80.0,
        },
        "results": rows,
    }

    out_path = args.output
    if out_path is None:
        date_str = datetime.now().strftime("%Y%m%d")
        out_path = ROOT / f"log/analysis/medicine_kb_baseline_{date_str}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {out_path}")
    for r in rows:
        mark = "OK" if r.get("pass") else "NG"
        print(
            f"  [{mark}] {r.get('id')}: top_score={r.get('top_score')} "
            f"chunks={r.get('chunk_count')} prefix={r.get('prefix_pass')}"
        )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
