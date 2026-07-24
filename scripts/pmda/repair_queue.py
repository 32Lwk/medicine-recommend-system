#!/usr/bin/env python3
"""live_fetch_queue 修復 CLI。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.queue import migrate_failed_to_done, queue_stats  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair PMDA live fetch queue")
    parser.add_argument("--source", required=True, choices=["interactions", "side_effects", "otc"])
    parser.add_argument("--reason", required=True, help="failed reason to migrate to done")
    args = parser.parse_args()

    before = queue_stats(args.source)
    result = migrate_failed_to_done(args.source, reason=args.reason)
    after = queue_stats(args.source)
    print(json.dumps({"before": before, "repair": result, "after": after}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
