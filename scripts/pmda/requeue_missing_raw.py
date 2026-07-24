#!/usr/bin/env python3
"""raw 未保存の done 成分を pending 先頭へ戻す（HTML 再取得用）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.queue import requeue_done_missing_raw, queue_stats  # noqa: E402
from scripts.pmda.raw_store import raw_stats  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-queue done ingredients missing PMDA raw HTML")
    parser.add_argument(
        "--include-failed-empty",
        action="store_true",
        help="Also re-queue failed with empty_section (no HTML saved yet)",
    )
    args = parser.parse_args()

    before = {**queue_stats("interactions"), **{"raw": raw_stats()}}
    result = requeue_done_missing_raw(include_failed=args.include_failed_empty)
    after = {**queue_stats("interactions"), **{"raw": raw_stats()}}
    payload = {"before": before, "after": after, **result}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
