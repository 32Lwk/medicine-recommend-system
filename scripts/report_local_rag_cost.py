#!/usr/bin/env python3
"""local_rag_detail.jsonl から embed コスト見積を集計。

Usage:
  .venv/bin/python scripts/report_local_rag_cost.py
  .venv/bin/python scripts/report_local_rag_cost.py --days 30
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]

# OpenAI embedding 単価（USD / 1M input tokens, 2026 参考）
PRICE_PER_1M = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
}
CHARS_PER_TOKEN = 4.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate local RAG embed cost from JSONL")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--log",
        type=Path,
        default=ROOT / "log" / "local_rag_detail.jsonl",
    )
    args = parser.parse_args()

    if not args.log.is_file():
        print(json.dumps({"error": "log not found", "path": str(args.log)}, indent=2))
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, args.days))
    embed_calls = 0
    cache_hits = 0
    tokens_est = 0.0
    by_model: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "cache_hits": 0, "tokens_est": 0.0}
    )
    retrieve_ms: list[float] = []

    for line in args.log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_raw = row.get("timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts < cutoff:
            continue
        if row.get("event") == "embed":
            model = str(row.get("local_rag_embed_model") or "unknown")
            chars = int(row.get("local_rag_embed_query_chars") or 0)
            hit = bool(row.get("local_rag_embed_cache_hit"))
            if hit:
                cache_hits += 1
                by_model[model]["cache_hits"] += 1
            else:
                embed_calls += 1
                tok = chars / CHARS_PER_TOKEN
                tokens_est += tok
                by_model[model]["calls"] += 1
                by_model[model]["tokens_est"] += tok
        elif row.get("event") == "retrieve":
            ms = row.get("local_rag_retrieve_ms")
            if ms is not None:
                retrieve_ms.append(float(ms))

    cost_usd = 0.0
    model_summary: Dict[str, Any] = {}
    for model, stats in by_model.items():
        rate = PRICE_PER_1M.get(model, 0.10)
        usd = (stats["tokens_est"] / 1_000_000) * rate
        cost_usd += usd
        model_summary[model] = {
            **stats,
            "tokens_est": round(stats["tokens_est"], 1),
            "cost_usd_est": round(usd, 4),
        }

    report = {
        "period_days": args.days,
        "embed_api_calls": embed_calls,
        "embed_cache_hits": cache_hits,
        "embed_tokens_est": round(tokens_est, 1),
        "embed_cost_usd_est": round(cost_usd, 4),
        "retrieve_samples": len(retrieve_ms),
        "retrieve_p50_ms": round(sorted(retrieve_ms)[len(retrieve_ms) // 2], 2)
        if retrieve_ms
        else 0.0,
        "by_model": model_summary,
        "log_path": str(args.log),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
