#!/usr/bin/env python3
"""PMDA 成分 live 連続 fetch（Cursor Cloud Agent 並列シャード対応）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import extract_otc_ingredients, record_live_fetch_session, write_otc_ingredients_json  # noqa: E402
from scripts.pmda.ingredient_parallel import (  # noqa: E402
    merge_shards_to_manifest,
    prepare_ingredient_shards,
    shard_stats,
)
from scripts.pmda.queue import init_live_fetch_queue, queue_stats, save_live_fetch_queue  # noqa: E402
from scripts.pmda.run_live_fetch_local import run_local_fetch  # noqa: E402


def _progress_snapshot(extra: Dict[str, Any], *, shard_id: Optional[int], shard_count: Optional[int]) -> Dict[str, Any]:
    if shard_id is not None and shard_count is not None:
        stats = shard_stats(shard_id, shard_count)
        return {
            "shard": stats,
            "mode": "cloud_ingredients_parallel",
            **extra,
        }
    ix = queue_stats("interactions")
    pending = ix.get("pending", 0)
    done = ix.get("done", 0)
    failed = len(ix.get("failed") or {})
    total = pending + done + failed
    pct = round(100.0 * done / total, 1) if total else 0.0
    return {
        "queue_interactions": ix,
        "ingredient_total": total,
        "ingredient_done_pct": pct,
        "mode": "cloud_ingredients",
        **extra,
    }


def prepare_full_ingredient_queue(*, requeue_failed: bool = False) -> Dict[str, Any]:
    """OTC CSV 全 1,337 成分で interactions/side_effects キューを再構築。"""
    ingredients = extract_otc_ingredients()
    write_otc_ingredients_json(ingredients)
    queue = init_live_fetch_queue(["interactions", "side_effects"])
    if requeue_failed:
        for source in ("interactions", "side_effects"):
            bucket = queue[source]
            failed = bucket.get("failed") or {}
            pending = list(bucket.get("pending") or [])
            for name in failed.keys():
                if name not in pending:
                    pending.append(name)
            bucket["failed"] = {}
            bucket["pending"] = pending
    save_live_fetch_queue(queue)
    return {
        "otc_unique_ingredients": len(ingredients),
        "queue_interactions": queue_stats("interactions"),
        "queue_side_effects": queue_stats("side_effects"),
        "requeue_failed": requeue_failed,
    }


def run_cloud_ingredient_fetch(
    *,
    min_interval: float = 1.0,
    merge_every: int = 50,
    max_hours: float = 12.0,
    allow_daytime: bool = True,
    fast_backfill: bool = False,
    shard_id: Optional[int] = None,
    shard_count: Optional[int] = None,
) -> Dict[str, Any]:
    started = time.time()
    deadline = started + max_hours * 3600.0
    result = run_local_fetch(
        min_interval=min_interval,
        merge_every=merge_every,
        allow_daytime=allow_daytime,
        ignore_daily_limit=True,
        ignore_session_gap=True,
        fast_backfill=fast_backfill,
        shard_id=shard_id,
        shard_count=shard_count,
    )
    elapsed_h = round((time.time() - started) / 3600.0, 2)
    payload = _progress_snapshot(
        {**result, "elapsed_hours": elapsed_h},
        shard_id=shard_id,
        shard_count=shard_count,
    )
    if time.time() > deadline and not result.get("ok"):
        payload["stopped_reason"] = "max_hours"
        payload["ok"] = False
    record_live_fetch_session(
        stats=payload,
        aborted=bool(result.get("aborted")),
        abort_reason=str(result.get("abort_reason") or ""),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="PMDA Cloud ingredient live fetch (parallel shard)")
    parser.add_argument("--prepare-queue", action="store_true", help="Rebuild global queue from OTC CSV")
    parser.add_argument("--requeue-failed", action="store_true", help="With --prepare-queue, move failed → pending")
    parser.add_argument(
        "--prepare-shards",
        type=int,
        metavar="N",
        help="Split global pending into N parallel shard files (after optional requeue)",
    )
    parser.add_argument("--shard-id", type=int, help="This worker shard id (0 .. shard-count-1)")
    parser.add_argument("--shard-count", type=int, help="Total parallel workers")
    parser.add_argument("--merge-shards", action="store_true", help="Merge shard done/failed into manifest")
    parser.add_argument("--min-interval", type=float, default=1.0)
    parser.add_argument("--merge-every", type=int, default=50)
    parser.add_argument("--max-hours", type=float, default=12.0)
    parser.add_argument("--allow-daytime", action="store_true", default=True)
    parser.add_argument("--fast-backfill", action="store_true")
    parser.add_argument("--fetch-only", action="store_true", help="Skip fetch (prepare/merge only)")
    args = parser.parse_args()

    if args.prepare_queue:
        info = prepare_full_ingredient_queue(requeue_failed=args.requeue_failed)
        print(json.dumps({"prepare_queue": info}, ensure_ascii=False, indent=2))

    if args.prepare_shards:
        if not args.prepare_queue:
            prepare_full_ingredient_queue(requeue_failed=args.requeue_failed)
        shard_info = prepare_ingredient_shards(
            args.prepare_shards,
            requeue_failed=False,
        )
        print(json.dumps({"prepare_shards": shard_info}, ensure_ascii=False, indent=2))

    if args.merge_shards:
        count = args.shard_count or args.prepare_shards
        if not count:
            print("ERROR: --merge-shards requires --shard-count or prior --prepare-shards N", file=sys.stderr)
            return 1
        merged = merge_shards_to_manifest(count)
        print(json.dumps({"merge_shards": merged}, ensure_ascii=False, indent=2))

    if args.fetch_only:
        return 0

    shard_id = args.shard_id
    shard_count = args.shard_count
    if (shard_id is None) ^ (shard_count is None):
        print("ERROR: pass both --shard-id and --shard-count for parallel worker", file=sys.stderr)
        return 1

    result = run_cloud_ingredient_fetch(
        min_interval=args.min_interval,
        merge_every=args.merge_every,
        max_hours=args.max_hours,
        allow_daytime=args.allow_daytime,
        fast_backfill=args.fast_backfill,
        shard_id=shard_id,
        shard_count=shard_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
