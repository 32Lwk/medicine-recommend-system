#!/usr/bin/env python3
"""ゴールデンケース JSONL のオフライン検証 CLI（P0-09）"""
from __future__ import annotations

import subprocess
import sys

if __name__ == "__main__":
    rc = subprocess.call(
        [sys.executable, "-m", "pytest", "tests/test_golden_regression.py", "-q"],
    )
    raise SystemExit(rc)
