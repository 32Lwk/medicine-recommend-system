#!/usr/bin/env python3
"""PMDA OTC live 連続 fetch（Cloud Agent 用・4h gap / 日次上限無効）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import record_live_fetch_session  # noqa: E402
from scripts.pmda.fetch_otc import (  # noqa: E402
    process_otc_product,
    write_otc_orphans,
    write_otc_staging,
)
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.merge_into_csv import merge_otc_products  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    check_live_fetch_guards,
    mark_queue_done,
    mark_queue_failed,
    pop_queue_batch,
    queue_stats,
    restore_queue_pending,
    write_cloud_otc_progress,
)


def _progress_payload(session: PmdaLiveSession, run_stats: Dict[str, Any]) -> Dict[str, Any]:
    q = queue_stats("otc")
    processed = run_stats["hits"] + run_stats["orphans"]
    hit_rate = round(100.0 * run_stats["hits"] / processed, 1) if processed else 0.0
    return {
        "queue_otc": q,
        "http_requested": session.stats.requested,
        "http_errors": session.stats.errors,
        "http_hits": session.stats.hits,
        "aborted": session.stats.aborted,
        "abort_reason": session.stats.abort_reason,
        "hit_rate_pct": hit_rate,
        **run_stats,
    }


def _print_progress(started: float, session: PmdaLiveSession, run_stats: Dict[str, Any]) -> None:
    q = queue_stats("otc")
    elapsed_m = int((time.time() - started) / 60)
    processed = run_stats["hits"] + run_stats["orphans"]
    hit_rate = round(100.0 * run_stats["hits"] / processed, 1) if processed else 0.0
    pending = q["pending"]
    # ~2 HTTP/item * ~3.5s ≈ 7s/item
    eta_h = round(pending * 7.0 / 3600.0, 1)
    print(
        f"[cloud-otc +{elapsed_m}m] HTTP: {session.stats.requested} | "
        f"hits: {run_stats['hits']} | errors: {session.stats.errors} | "
        f"pending: {pending}/7495\n"
        f"  hit_rate: {hit_rate}% | orphans: {run_stats['orphans']} | "
        f"abort: {str(session.stats.aborted).lower()}\n"
        f"  ETA: ~{eta_h}h",
        flush=True,
    )


def run_cloud_otc_fetch(
    *,
    min_interval: float = 1.0,
    merge_every: int = 100,
    resume: bool = True,
    max_hours: float = 20.0,
    allow_daytime: bool = True,
) -> Dict[str, Any]:
    ok, reason = check_live_fetch_guards(
        allow_daytime=allow_daytime,
        ignore_daily_limit=True,
        ignore_session_gap=True,
    )
    if not ok:
        return {"ok": False, "stage": "guard", "reason": reason}

    # resume は manifest live_fetch_queue.otc を正本（追加 init しない）
    _ = resume

    current_interval = max(1.0, min_interval)
    session = PmdaLiveSession(min_interval_sec=current_interval, batch_size=0)
    started = time.time()
    last_progress = started
    deadline = started + max_hours * 3600.0
    buffer: List[Dict[str, Any]] = []
    orphans: List[Dict[str, Any]] = []
    http403_retries = 0
    run_stats: Dict[str, Any] = {
        "processed": 0,
        "hits": 0,
        "orphans": 0,
        "merge_runs": 0,
        "min_interval": current_interval,
        "http403_retries": 0,
        "stopped_reason": "",
    }

    def _flush_merge() -> Dict[str, Any]:
        if not buffer:
            return {"ok": True, "skipped": True}
        write_otc_staging(buffer, {"mode": "live", "batch": len(buffer)})
        merge_result = merge_otc_products(list(buffer), pmda_priority=True)
        buffer.clear()
        run_stats["merge_runs"] += 1
        return {"ok": True, "merge": merge_result}

    try:
        while queue_stats("otc")["pending"] > 0:
            if time.time() >= deadline:
                run_stats["stopped_reason"] = "max_hours"
                break
            if session.stats.aborted:
                reason = session.stats.abort_reason or ""
                if "HTTP 403" in reason and http403_retries == 0:
                    pending_restore: List[str] = []
                    print("[cloud-otc] HTTP 403 — wait 10 min, resume with --min-interval 2", flush=True)
                    time.sleep(600)
                    http403_retries = 1
                    run_stats["http403_retries"] = 1
                    current_interval = max(2.0, current_interval)
                    run_stats["min_interval"] = current_interval
                    session.close()
                    session = PmdaLiveSession(min_interval_sec=current_interval, batch_size=0)
                    continue
                run_stats["stopped_reason"] = reason
                break

            batch = pop_queue_batch("otc", max_items=1)
            if not batch:
                break
            key = batch[0]
            try:
                result = process_otc_product(session, key)
            except PmdaFetchAborted as exc:
                restore_queue_pending("otc", [key])
                session.stats.aborted = True
                session.stats.abort_reason = str(exc)
                continue

            if result["status"] == "aborted":
                restore_queue_pending("otc", [key])
                # session already aborted; loop handles 403 retry / stop
                continue

            run_stats["processed"] += 1
            if result["status"] == "done" and result.get("row"):
                mark_queue_done("otc", [key])
                run_stats["hits"] += 1
                buffer.append(result["row"])
            else:
                reason = result.get("reason") or "not_found"
                mark_queue_failed("otc", key, reason)
                run_stats["orphans"] += 1
                orphans.append(
                    {
                        "key": key,
                        "product_name": result.get("product_name") or "",
                        "manufacturer": result.get("manufacturer") or "",
                        "search_name": result.get("search_name") or "",
                        "reason": reason,
                        "score": result.get("score") or 0,
                    }
                )

            if run_stats["processed"] % merge_every == 0:
                merge_result = _flush_merge()
                if not merge_result.get("ok"):
                    return {"ok": False, "stage": "merge", "merge_result": merge_result, **run_stats}
                write_otc_orphans(orphans)

            now = time.time()
            if now - last_progress >= 600:
                write_cloud_otc_progress(_progress_payload(session, run_stats))
                _print_progress(started, session, run_stats)
                last_progress = now

        if buffer:
            _flush_merge()
        if orphans:
            write_otc_orphans(orphans)

    except PmdaFetchAborted as exc:
        session.stats.aborted = True
        session.stats.abort_reason = str(exc)
        run_stats["stopped_reason"] = str(exc)

    elapsed = round(time.time() - started, 1)
    q_after = queue_stats("otc")
    processed_total = q_after["done"] + q_after["failed"]
    hit_rate = round(100.0 * q_after["done"] / processed_total, 1) if processed_total else 0.0
    final = {
        "ok": (
            not session.stats.aborted
            and q_after["pending"] == 0
            and hit_rate >= 95.0
        ),
        "elapsed_sec": elapsed,
        "queue_otc": q_after,
        "http_requested": session.stats.requested,
        "http_errors": session.stats.errors,
        "http_hits": session.stats.hits,
        "aborted": session.stats.aborted,
        "abort_reason": session.stats.abort_reason,
        "hit_rate_pct": hit_rate,
        **run_stats,
    }
    write_cloud_otc_progress(final)
    _print_progress(started, session, run_stats)
    record_live_fetch_session(
        stats={"mode": "cloud_otc", **final},
        aborted=session.stats.aborted,
        abort_reason=session.stats.abort_reason or "",
    )
    session.close()
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="PMDA Cloud OTC continuous live fetch")
    parser.add_argument("--min-interval", type=float, default=1.0)
    parser.add_argument("--merge-every", type=int, default=100)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--max-hours", type=float, default=20.0)
    parser.add_argument("--allow-daytime", action="store_true", default=True)
    args = parser.parse_args()

    result = run_cloud_otc_fetch(
        min_interval=args.min_interval,
        merge_every=args.merge_every,
        resume=args.resume,
        max_hours=args.max_hours,
        allow_daytime=args.allow_daytime,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("aborted") and "HTTP 403" in (result.get("abort_reason") or ""):
        return 2
    if result.get("aborted") and "HTTP 429" in (result.get("abort_reason") or ""):
        return 2
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
