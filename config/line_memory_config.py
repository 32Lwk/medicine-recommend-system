"""LINE 長期記憶・プロファイル設定。"""
from __future__ import annotations

import os


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def line_memory_recent_turns() -> int:
    """LLM に渡す直近ターン数（圧縮会話）。"""
    return max(0, _get_int("LINE_MEMORY_RECENT_TURNS", 5))


def line_memory_summary_max() -> int:
    """保持するエピソード要約の最大件数。"""
    return max(1, _get_int("LINE_MEMORY_SUMMARY_MAX", 5))
