#!/usr/bin/env python3
"""PMDA 成分 live 連続 fetch（§10+§11 統合、ローカル完走用）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    INTERACTIONS_CSV,
    SIDE_EFFECTS_CSV,
    load_common_rx_medications,
    record_live_fetch_session,
)
from scripts.pmda.fetch_ingredient_live import (  # noqa: E402
    merge_staging_to_csv,
    process_ingredient,
    update_queues_for_ingredient,
    write_staging_batch,
)
from scripts.pmda.http_client import PMDA_LIVE_SOURCE_LABELS, PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import normalize_interaction_row, normalize_side_effect_row  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    check_live_fetch_guards,
    pop_queue_batch,
    queue_stats,
    restore_queue_pending,
    sync_side_effects_queue_from_interactions,
    write_local_ingredients_progress,
)
from scripts.pmda.raw_store import raw_stats  # noqa: E402


def _count_pmda_rows() -> Dict[str, int]:
    from scripts.pmda.common import read_csv_rows

    ix = sum(
        1
        for row in read_csv_rows(INTERACTIONS_CSV)
        if (normalize_interaction_row(row) or {}).get("出典") in PMDA_LIVE_SOURCE_LABELS
    )
    se = sum(
        1
        for row in read_csv_rows(SIDE_EFFECTS_CSV)
        if (normalize_side_effect_row(row) or {}).get("出典") in PMDA_LIVE_SOURCE_LABELS
    )
    return {"interactions": ix, "side_effects": se}


def _progress_payload(session: PmdaLiveSession, run_stats: Dict[str, Any]) -> Dict[str, Any]:
    pmda = _count_pmda_rows()
    return {
        "queue_interactions": queue_stats("interactions"),
        "queue_side_effects": queue_stats("side_effects"),
        "pmda_rows": pmda,
        "raw_files": raw_stats(),
        "http_requested": session.stats.requested,
        "http_errors": session.stats.errors,
        "http_hits": session.stats.hits,
        "aborted": session.stats.aborted,
        "abort_reason": session.stats.abort_reason,
        **run_stats,
    }


def run_local_fetch(
    *,
    min_interval: float = 1.0,
    merge_every: int = 50,
    allow_daytime: bool = True,
    ignore_daily_limit: bool = True,
    ignore_session_gap: bool = True,
    fast_backfill: bool = False,
    shard_id: Optional[int] = None,
    shard_count: Optional[int] = None,
) -> Dict[str, Any]:
    import importlib
    import scripts.pmda.http_client as http_client_mod

    importlib.reload(http_client_mod)
    if not hasattr(http_client_mod.PmdaLiveSession, "fetch_ingredient_sections"):
        raise RuntimeError(
            f"fetch_ingredient_sections missing on PmdaLiveSession ({http_client_mod.__file__})"
        )

    ok, reason = check_live_fetch_guards(
        allow_daytime=allow_daytime,
        ignore_daily_limit=ignore_daily_limit,
        ignore_session_gap=ignore_session_gap,
    )
    if not ok:
        return {"ok": False, "stage": "guard", "reason": reason}

    sync_info = sync_side_effects_queue_from_interactions()
    partners = load_common_rx_medications()
    session = http_client_mod.PmdaLiveSession(
        min_interval_sec=min_interval,
        batch_size=0,
        fast_backfill=fast_backfill,
    )
    started = time.time()
    last_progress = started

    ix_buffer: List[Dict[str, Any]] = []
    se_buffer: List[Dict[str, Any]] = []
    run_stats: Dict[str, Any] = {
        "processed": 0,
        "done": 0,
        "failed": 0,
        "no_data_ix": 0,
        "no_data_se": 0,
        "merge_runs": 0,
        "raw_saved": 0,
        "fast_backfill": fast_backfill,
        "sync": sync_info,
        "shard_id": shard_id,
        "shard_count": shard_count,
    }

    use_shard = shard_id is not None and shard_count is not None

    def _pending_count() -> int:
        if use_shard:
            from scripts.pmda.ingredient_parallel import shard_stats

            return shard_stats(shard_id, shard_count)["pending"]
        return queue_stats("interactions")["pending"]

    def _pop_batch() -> List[str]:
        if use_shard:
            from scripts.pmda.ingredient_parallel import pop_shard_batch

            return pop_shard_batch(shard_id, shard_count, max_items=1)
        return pop_queue_batch("interactions", max_items=1)

    def _restore_pending(items: List[str]) -> None:
        if not items:
            return
        if use_shard:
            from scripts.pmda.ingredient_parallel import load_shard, save_shard

            data = load_shard(shard_id, shard_count)
            pending = list(data.get("pending") or [])
            for item in items:
                if item not in pending:
                    pending.insert(0, item)
            data["pending"] = pending
            save_shard(data)
        else:
            restore_queue_pending("interactions", items)
            restore_queue_pending("side_effects", items)

    def _apply_result(result: Dict[str, Any]) -> None:
        ingredient = result["ingredient"]
        status = result["status"]
        if use_shard:
            from scripts.pmda.ingredient_parallel import mark_shard_done, mark_shard_failed

            if status == "done":
                mark_shard_done(shard_id, shard_count, [ingredient])
            elif status == "failed":
                mark_shard_failed(shard_id, shard_count, ingredient, result.get("reason") or "failed")
        else:
            update_queues_for_ingredient(result)

    try:
        with session:
            while _pending_count() > 0:
                if session.stats.aborted:
                    break
                batch = _pop_batch()
                if not batch:
                    break
                ingredient = batch[0]
                pending_restore = [ingredient]

                result = process_ingredient(session, ingredient, partners)
                if result["status"] == "aborted":
                    _restore_pending(pending_restore)
                    break

                _apply_result(result)
                pending_restore.clear()
                run_stats["processed"] += 1

                if result["status"] == "done":
                    run_stats["done"] += 1
                    if result.get("raw_saved"):
                        run_stats["raw_saved"] += 1
                    if result.get("no_data_ix"):
                        run_stats["no_data_ix"] += 1
                    if result.get("no_data_se"):
                        run_stats["no_data_se"] += 1
                    ix_buffer.extend(result["ix_rows"])
                    se_buffer.extend(result["se_rows"])
                else:
                    run_stats["failed"] += 1
                    if result.get("raw_saved"):
                        run_stats["raw_saved"] += 1

                if run_stats["processed"] % merge_every == 0 and (ix_buffer or se_buffer):
                    write_staging_batch(ix_buffer, se_buffer, {"mode": "live", "batch": merge_every})
                    merge_result = merge_staging_to_csv()
                    run_stats["merge_runs"] += 1
                    ix_buffer.clear()
                    se_buffer.clear()
                    if not merge_result.get("ok"):
                        return {"ok": False, "stage": "merge", "merge_result": merge_result, **run_stats}

                now = time.time()
                if now - last_progress >= 300:
                    write_local_ingredients_progress(_progress_payload(session, run_stats))
                    last_progress = now

        if not session.stats.aborted and (ix_buffer or se_buffer):
            write_staging_batch(ix_buffer, se_buffer, {"mode": "live", "final": True})
            merge_result = merge_staging_to_csv()
            run_stats["merge_runs"] += 1
            if not merge_result.get("ok"):
                return {"ok": False, "stage": "merge", "merge_result": merge_result, **run_stats}

    except PmdaFetchAborted as exc:
        session.stats.aborted = True
        session.stats.abort_reason = str(exc)

    elapsed = round(time.time() - started, 1)
    final = {
        "ok": (not session.stats.aborted and _pending_count() == 0),
        "elapsed_sec": elapsed,
        "pmda_rows": _count_pmda_rows(),
        "queue_interactions": queue_stats("interactions"),
        "queue_side_effects": queue_stats("side_effects"),
        "http_requested": session.stats.requested,
        "http_errors": session.stats.errors,
        "aborted": session.stats.aborted,
        "abort_reason": session.stats.abort_reason,
        **run_stats,
    }
    write_local_ingredients_progress(final)
    record_live_fetch_session(
        stats={"mode": "local_ingredients", **final},
        aborted=session.stats.aborted,
        abort_reason=session.stats.abort_reason or "",
    )
    session.close()
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="PMDA local continuous ingredient live fetch")
    parser.add_argument("--min-interval", type=float, default=1.0)
    parser.add_argument("--merge-every", type=int, default=50)
    parser.add_argument("--allow-daytime", action="store_true", default=True)
    parser.add_argument("--ignore-daily-limit", action="store_true", default=True)
    parser.add_argument("--ignore-session-gap", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true", help="Resume from manifest queue (sync side_effects done)")
    parser.add_argument(
        "--fast-backfill",
        action="store_true",
        help="Raw backfill: jitter 0.8-1.5s/request (default 2.5-5.0s). Watch for HTTP 403/429.",
    )
    args = parser.parse_args()

    if args.resume:
        sync_info = sync_side_effects_queue_from_interactions()
        print(json.dumps({"resume_sync": sync_info}, ensure_ascii=False), file=sys.stderr)

    result = run_local_fetch(
        min_interval=args.min_interval,
        merge_every=args.merge_every,
        allow_daytime=args.allow_daytime,
        ignore_daily_limit=args.ignore_daily_limit,
        ignore_session_gap=args.ignore_session_gap,
        fast_backfill=args.fast_backfill,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
