"""tests 配下から参照するプロジェクトパス（深さに依存しない）。"""
from __future__ import annotations

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
TEST_SNAPSHOTS_DIR = PROJECT_ROOT / "test_snapshots"
