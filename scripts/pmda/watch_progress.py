#!/usr/bin/env python3
"""PMDA live fetch 進捗を別ターミナルからリアルタイム表示。

Usage:
  .venv/bin/python scripts/pmda/watch_progress.py
  .venv/bin/python scripts/pmda/watch_progress.py --interval 15
  .venv/bin/python scripts/pmda/watch_progress.py --once
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import INTERACTIONS_CSV, SIDE_EFFECTS_CSV, read_csv_rows  # noqa: E402
from scripts.pmda.http_client import PMDA_LIVE_SOURCE_LABELS  # noqa: E402
from scripts.pmda.normalize import normalize_interaction_row, normalize_side_effect_row  # noqa: E402
from scripts.pmda.queue import queue_stats  # noqa: E402

SEC_PER_INGREDIENT = 3.9


def _fetch_running() -> bool:
    return (
        subprocess.run(
            ["pgrep", "-f", "run_live_fetch_local"],
            capture_output=True,
        ).returncode
        == 0
    )


def _pmda_row_counts() -> tuple[int, int]:
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
    return ix, se


def render_progress(*, prev_pending: int | None = None) -> tuple[str, int]:
    st = queue_stats("interactions")
    pending = st["pending"]
    done = st["done"]
    failed = st["failed"]
    total = st["total"]
    processed = done + failed
    pct = 100.0 * processed / total if total else 0.0
    eta_min = pending * SEC_PER_INGREDIENT / 60.0
    running = _fetch_running()
    ix, se = _pmda_row_counts()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    delta = ""
    if prev_pending is not None and prev_pending != pending:
        delta = f"  (pending {prev_pending - pending:+d})"

    lines = [
        f"[{now}] fetch: {'RUNNING' if running else 'STOPPED'}",
        f"pending {pending}{delta} | done {done} | failed {failed} | {processed}/{total} ({pct:.1f}%)",
        f"ETA ~{eta_min:.0f} min (~{eta_min / 60:.1f} h) | PMDA iyakuSearch ix/se: {ix}/{se}",
    ]
    return "\n".join(lines), pending


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch PMDA local fetch progress")
    parser.add_argument("--interval", type=int, default=30, help="Refresh seconds (default 30)")
    parser.add_argument("--once", action="store_true", help="Print once and exit")
    args = parser.parse_args()

    prev: int | None = None
    while True:
        if not args.once:
            print("\033[2J\033[H", end="")  # clear screen
        text, prev = render_progress(prev_pending=prev)
        print(text)
        if args.once:
            return 0
        if queue_stats("interactions")["pending"] == 0:
            print("\n✓ interactions queue complete")
            return 0
        try:
            time.sleep(max(1, args.interval))
        except KeyboardInterrupt:
            print("\n(stopped watching)")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
