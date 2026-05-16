"""
ルーティング・トリアージ関連の環境変数
"""
from __future__ import annotations

import os


def _get_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def triage_confidence_threshold() -> float:
    return _get_float("TRIAGE_CONFIDENCE_THRESHOLD", 0.75)


def triage_history_messages() -> int:
    return max(0, _get_int("TRIAGE_HISTORY_MESSAGES", 5))
