#!/usr/bin/env python3
"""PMDA live fetch 1 セッション: fetch → validate → merge。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    INTERACTIONS_CSV,
    SIDE_EFFECTS_CSV,
    read_csv_rows,
)
from scripts.pmda.http_client import PMDA_LIVE_SOURCE_LABELS  # noqa: E402
from scripts.pmda.normalize import normalize_interaction_row, normalize_side_effect_row  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    append_live_batch_log,
    check_live_fetch_guards,
    estimate_sessions_remaining,
    get_sessions_today,
    queue_stats,
    record_session_today,
)
from scripts.pmda.run_pmda_import import run_import  # noqa: E402

SOURCE_BATCH_DEFAULTS = {
    "interactions": {"ingredient_batch": 10, "live_batch_size": 30},
    "side_effects": {"ingredient_batch": 10, "live_batch_size": 30},
    "otc": {"ingredient_batch": 10, "live_batch_size": 10},
}


def _count_pmda_rows(source: str) -> int:
    if source == "interactions":
        return sum(
            1
            for row in read_csv_rows(INTERACTIONS_CSV)
            if (normalize_interaction_row(row) or {}).get("出典") in PMDA_LIVE_SOURCE_LABELS
        )
    if source == "side_effects":
        return sum(
            1
            for row in read_csv_rows(SIDE_EFFECTS_CSV)
            if (normalize_side_effect_row(row) or {}).get("出典") in PMDA_LIVE_SOURCE_LABELS
        )
    return 0


def run_batch(
    *,
    source: str,
    resume: bool = True,
    min_interval: float = 3.0,
    force: bool = False,
    allow_daytime: bool = False,
) -> dict:
    ok, reason = check_live_fetch_guards(force=force, allow_daytime=allow_daytime)
    if not ok:
        return {"ok": False, "stage": "guard", "reason": reason}

    defaults = SOURCE_BATCH_DEFAULTS[source]
    before_stats = queue_stats(source)
    before_pmda = _count_pmda_rows(source)

    result = run_import(
        sources=[source],
        live=True,
        dry_run=False,
        min_interval=min_interval,
        live_batch_size=defaults["live_batch_size"],
        resume=resume,
        ingredient_batch=defaults["ingredient_batch"],
        allow_daytime=allow_daytime,
        force=force,
    )

    after_stats = queue_stats(source)
    after_pmda = _count_pmda_rows(source)
    sessions_left = estimate_sessions_remaining(source, defaults["ingredient_batch"] if source != "otc" else 10)

    summary = {
        "source": source,
        "ok": result.get("ok"),
        "stage": result.get("stage"),
        "fetch_stats": result.get("fetch_stats"),
        "merge_stats": result.get("merge_stats"),
        "queue_before": before_stats,
        "queue_after": after_stats,
        "pmda_rows_before": before_pmda,
        "pmda_rows_after": after_pmda,
        "sessions_remaining_est": sessions_left,
        "sessions_today": get_sessions_today(),
        "abort": bool((result.get("fetch_stats") or {}).get(source, {}).get("abort_reason")),
    }
    if result.get("ok") and not summary["abort"]:
        summary["sessions_today"] = record_session_today()
    append_live_batch_log(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one PMDA live fetch batch session")
    parser.add_argument("--source", required=True, choices=["interactions", "side_effects", "otc"])
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--min-interval", type=float, default=3.0)
    parser.add_argument("--force", action="store_true", help="Skip all guards (tests only)")
    parser.add_argument("--allow-daytime", action="store_true", help="Skip JST time window guard (4h gap still enforced)")
    args = parser.parse_args()

    summary = run_batch(
        source=args.source,
        resume=args.resume,
        min_interval=args.min_interval,
        force=args.force,
        allow_daytime=args.allow_daytime,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    pending = (summary.get("queue_after") or {}).get("pending", "?")
    eta = summary.get("sessions_remaining_est", "?")
    print(f"\nPending: {pending} | ETA sessions: {eta} | PMDA rows: {summary.get('pmda_rows_after')}")
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
