#!/usr/bin/env python3
"""Local RAG retrieve レイテンシ benchmark（fixture ベース）。"""
from __future__ import annotations

import argparse
import json
import statistics
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


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_vals = sorted(values)
    idx = int(round(0.95 * (len(sorted_vals) - 1)))
    return sorted_vals[idx]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local RAG retrieve latency")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--p95-target-ms",
        type=float,
        default=800.0,
        help="Warn if P95 exceeds this (default 800ms)",
    )
    args = parser.parse_args()

    from src.services.bedrock_kb_retrieve import build_concierge_retrieval_query
    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_index import get_bm25_index

    # 初回 index build のコールドスタートを計測から除外
    get_bm25_index("medicine")
    get_bm25_index("concierge")
    retrieve_local_context("warmup", namespace="medicine", top_k=1, min_score=0.0)
    retrieve_local_context("warmup", namespace="concierge", top_k=1, min_score=0.0)

    medicine_fixture = _load_yaml(ROOT / "tests/fixtures/medicine_kb_eval.yaml")
    concierge_fixture = _load_yaml(ROOT / "tests/fixtures/concierge_kb_eval.yaml")

    rows: List[Dict[str, Any]] = []

    for sc in medicine_fixture.get("scenarios") or []:
        query = str(sc.get("query") or "").strip()
        retrieval_query = query
        recommended = []
        for item in sc.get("recommended_medicines") or []:
            if isinstance(item, str):
                recommended.append({"product_name": item})
            elif isinstance(item, dict):
                recommended.append(dict(item))
        result = retrieve_local_context(
            retrieval_query,
            namespace="medicine",
            top_k=5,
            min_score=0.4,
            recommended_medicines=recommended,
            category=str(sc.get("category") or ""),
        )
        rows.append(
            {
                "id": sc.get("id"),
                "namespace": "medicine",
                "kb_retrieve_ms": float(result.get("kb_retrieve_ms") or 0),
                "route": result.get("route"),
            }
        )

    for sc in concierge_fixture.get("scenarios") or []:
        user_query = str(sc.get("query") or "").strip()
        intent = str(sc.get("intent") or "").strip()
        retrieval_query = build_concierge_retrieval_query(user_query, intent)
        result = retrieve_local_context(
            retrieval_query,
            namespace="concierge",
            top_k=5,
            min_score=0.4,
            intent=intent,
        )
        rows.append(
            {
                "id": sc.get("id"),
                "namespace": "concierge",
                "kb_retrieve_ms": float(result.get("kb_retrieve_ms") or 0),
            }
        )

    all_ms = [float(r["kb_retrieve_ms"]) for r in rows]
    by_ns: Dict[str, List[float]] = {}
    for row in rows:
        by_ns.setdefault(str(row["namespace"]), []).append(float(row["kb_retrieve_ms"]))

    summary: Dict[str, Any] = {
        "total_queries": len(rows),
        "p50_ms": round(statistics.median(all_ms), 2) if all_ms else 0.0,
        "p95_ms": round(_p95(all_ms), 2),
        "max_ms": round(max(all_ms), 2) if all_ms else 0.0,
        "p95_target_ms": args.p95_target_ms,
        "p95_within_target": _p95(all_ms) <= args.p95_target_ms if all_ms else True,
        "by_namespace": {
            ns: {
                "count": len(vals),
                "p95_ms": round(_p95(vals), 2),
                "max_ms": round(max(vals), 2),
            }
            for ns, vals in by_ns.items()
        },
    }

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "local_rag",
        "summary": summary,
        "results": rows,
    }

    out = args.output
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d")
        out = ROOT / f"log/analysis/local_rag_benchmark_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")

    if not summary["p95_within_target"]:
        print(
            f"WARN: P95 {summary['p95_ms']}ms exceeds target {args.p95_target_ms}ms",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
