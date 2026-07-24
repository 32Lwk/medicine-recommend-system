#!/usr/bin/env python3
"""Medicine Managed KB retrieve 評価（baseline / Phase 1 / 1.5 再計測）。

Usage:
  AWS_PROFILE=admin .venv/bin/python scripts/eval_medicine_kb.py
  AWS_PROFILE=admin .venv/bin/python scripts/eval_medicine_kb.py \
    --output log/analysis/medicine_kb_after_phase1_5_20260724.json \
    --use-retrieval-query --min-pass-pct 75 --min-interaction-pass 5
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

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _load_fixture(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _uri_matches_prefix(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    needle = prefix.strip("/")
    return needle in uri.replace("\\", "/")


def _recommended_from_scenario(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = scenario.get("recommended_medicines") or []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            name = item.strip()
            if name:
                out.append({"product_name": name})
        elif isinstance(item, dict):
            out.append(dict(item))
    return out


def _evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    kb_id: str,
    search_mode: str,
    top_k: int,
    mode: str,
) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import (
        build_medicine_retrieval_query,
        retrieve_kb_context,
    )

    query = str(scenario.get("query") or "").strip()
    min_score = float(scenario.get("min_score") or 0.5)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")
    recommended = _recommended_from_scenario(scenario)

    if mode == "runtime":
        retrieval_query = build_medicine_retrieval_query(
            query,
            recommended,
            use_comprehend=False,
        )
    else:
        retrieval_query = query

    result = retrieve_kb_context(
        retrieval_query,
        kb_id=kb_id,
        cache_namespace=f"medicine_eval_{mode}",
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
        "mode": mode,
        "query": query,
        "retrieval_query": retrieval_query,
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


def _interaction_pass_count(rows: List[Dict[str, Any]]) -> int:
    return sum(
        1
        for r in rows
        if r.get("category") == "interaction" and r.get("pass")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Medicine KB retrieve against fixture")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/medicine_kb_eval.yaml",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--phase", default="phase1_5_kb")
    parser.add_argument(
        "--use-retrieval-query",
        action="store_true",
        help="Also run runtime mode via build_medicine_retrieval_query",
    )
    parser.add_argument(
        "--mode",
        choices=("raw", "runtime", "both"),
        default="raw",
        help="Evaluation mode (default raw). 'both' runs raw + runtime.",
    )
    parser.add_argument(
        "--min-pass-pct",
        type=float,
        default=0.0,
        help="Fail if pass_all_pct below this (0=disabled, CI uses 75)",
    )
    parser.add_argument(
        "--min-interaction-pass",
        type=int,
        default=0,
        help="Fail if interaction pass count below this (CI uses 5)",
    )
    args = parser.parse_args()

    fixture = _load_fixture(args.fixture)
    kb_id = str(fixture.get("kb_id") or "30BCEJCJHA")
    search_mode = str(fixture.get("search_mode") or "managed")
    scenarios = fixture.get("scenarios") or []

    modes: List[str]
    if args.mode == "both" or args.use_retrieval_query:
        modes = ["raw", "runtime"]
    elif args.mode == "runtime":
        modes = ["runtime"]
    else:
        modes = ["raw"]

    all_rows: List[Dict[str, Any]] = []
    for mode in modes:
        for sc in scenarios:
            row = _evaluate_scenario(
                sc,
                kb_id=kb_id,
                search_mode=search_mode,
                top_k=args.top_k,
                mode=mode,
            )
            all_rows.append(row)

    primary_mode = "raw" if "raw" in modes else modes[0]
    primary_rows = [r for r in all_rows if r.get("mode") == primary_mode]
    passed = sum(1 for r in primary_rows if r.get("pass"))
    total = len(primary_rows)
    score_only = sum(1 for r in primary_rows if r.get("score_pass"))
    interaction_pass = _interaction_pass_count(primary_rows)

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "kb_id": kb_id,
        "search_mode": search_mode,
        "fixture": str(args.fixture.relative_to(ROOT)),
        "modes": modes,
        "summary": {
            "mode": primary_mode,
            "total": total,
            "pass_all": passed,
            "pass_all_pct": round(100.0 * passed / total, 1) if total else 0.0,
            "score_pass": score_only,
            "score_pass_pct": round(100.0 * score_only / total, 1) if total else 0.0,
            "interaction_pass": interaction_pass,
            "interaction_total": 5,
            "target_pass_pct": 80.0,
            "baseline_pass_pct": 75.0,
        },
        "results": all_rows,
    }

    if len(modes) > 1:
        for mode in modes:
            if mode == primary_mode:
                continue
            rows = [r for r in all_rows if r.get("mode") == mode]
            p = sum(1 for r in rows if r.get("pass"))
            report["summary"][f"{mode}_pass_all"] = p
            report["summary"][f"{mode}_pass_all_pct"] = round(
                100.0 * p / len(rows), 1
            ) if rows else 0.0

    out_path = args.output
    if out_path is None:
        date_str = datetime.now().strftime("%Y%m%d")
        out_path = ROOT / f"log/analysis/medicine_kb_baseline_{date_str}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {out_path}")
    for r in primary_rows:
        mark = "OK" if r.get("pass") else "NG"
        print(
            f"  [{mark}] {r.get('id')}: top_score={r.get('top_score')} "
            f"chunks={r.get('chunk_count')} prefix={r.get('prefix_pass')}"
        )

    exit_code = 0
    pct = report["summary"]["pass_all_pct"]
    if args.min_pass_pct > 0 and pct < args.min_pass_pct:
        print(f"FAIL: pass_all_pct {pct} < min {args.min_pass_pct}", file=sys.stderr)
        exit_code = 1
    if args.min_interaction_pass > 0 and interaction_pass < args.min_interaction_pass:
        print(
            f"FAIL: interaction_pass {interaction_pass} < min {args.min_interaction_pass}",
            file=sys.stderr,
        )
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
