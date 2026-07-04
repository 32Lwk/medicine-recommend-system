#!/usr/bin/env python3
"""競技・推奨文脈 localhost 統合テスト CLI。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.routing.test_medicine_context_live_integration import (  # noqa: E402
    DEFAULT_BASE,
    run_all_and_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Medicine context live integration tests")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE,
        help="App base URL (default: http://127.0.0.1:5000/)",
    )
    args = parser.parse_args()
    return run_all_and_report(args.base_url)


if __name__ == "__main__":
    raise SystemExit(main())
