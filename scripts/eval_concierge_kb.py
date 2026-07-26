#!/usr/bin/env python3
"""Concierge Managed KB retrieve 評価。

Usage:
  AWS_PROFILE=admin .venv/bin/python scripts/eval_concierge_kb.py
  AWS_PROFILE=admin .venv/bin/python scripts/eval_concierge_kb.py \
    --output log/analysis/concierge_kb_baseline_20260724.json
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
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _uri_matches_prefix(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    needle = prefix.strip("/")
    return needle in uri.replace("\\", "/")


def _evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    kb_id: str,
    search_mode: str,
    provider: str = "bedrock",
) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import (
        _concierge_kb_top_k,
        build_concierge_retrieval_query,
        retrieve_concierge_context,
        retrieve_kb_context,
    )

    user_query = str(scenario.get("query") or "").strip()
    intent = str(scenario.get("intent") or "").strip()
    min_score = float(scenario.get("min_score") or 0.5)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")

    retrieval_query = build_concierge_retrieval_query(user_query, intent)
    top_k = _concierge_kb_top_k(intent)
    if provider == "local":
        import os

        prev = os.environ.get("CONCIERGE_RAG_PROVIDER")
        os.environ["CONCIERGE_RAG_PROVIDER"] = "local"
        try:
            result = retrieve_concierge_context(
                retrieval_query,
                top_k=top_k,
                use_cache=False,
                intent=intent,
            )
        finally:
            if prev is None:
                os.environ.pop("CONCIERGE_RAG_PROVIDER", None)
            else:
                os.environ["CONCIERGE_RAG_PROVIDER"] = prev
    else:
        result = retrieve_kb_context(
            retrieval_query,
            kb_id=kb_id,
            cache_namespace="concierge_eval",
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
        "intent": intent,
        "query": user_query,
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
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Concierge KB retrieve")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/concierge_kb_eval.yaml",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--phase", default="phase4_concierge")
    parser.add_argument(
        "--min-pass-pct",
        type=float,
        default=0.0,
        help="Fail if pass_all_pct below this (CI uses 80)",
    )
    parser.add_argument(
        "--provider",
        choices=("bedrock", "local"),
        default="bedrock",
        help="Retrieve backend (bedrock=Managed KB API, local=local hybrid index)",
    )
    args = parser.parse_args()

    fixture = _load_fixture(args.fixture)
    kb_id = str(fixture.get("kb_id") or "2CNAGQ2V4P")
    search_mode = str(fixture.get("search_mode") or "managed")
    scenarios = fixture.get("scenarios") or []

    rows = [
        _evaluate_scenario(
            sc, kb_id=kb_id, search_mode=search_mode, provider=args.provider
        )
        for sc in scenarios
    ]
    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    score_only = sum(1 for r in rows if r.get("score_pass"))

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "provider": args.provider,
        "kb_id": kb_id,
        "search_mode": search_mode,
        "region": str(fixture.get("region") or "ap-northeast-1"),
        "fixture": str(args.fixture.relative_to(ROOT)),
        "summary": {
            "total": total,
            "pass_all": passed,
            "pass_all_pct": round(100.0 * passed / total, 1) if total else 0.0,
            "score_pass": score_only,
            "score_pass_pct": round(100.0 * score_only / total, 1) if total else 0.0,
        },
        "results": rows,
    }

    out_path = args.output
    if out_path is None:
        date_str = datetime.now().strftime("%Y%m%d")
        suffix = "local" if args.provider == "local" else "baseline"
        out_path = ROOT / f"log/analysis/concierge_kb_{suffix}_{date_str}.json"
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
    exit_code = 0
    pct = report["summary"]["pass_all_pct"]
    if args.min_pass_pct > 0 and pct < args.min_pass_pct:
        print(f"FAIL: pass_all_pct {pct} < min {args.min_pass_pct}", file=sys.stderr)
        exit_code = 1
    elif passed != total:
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
