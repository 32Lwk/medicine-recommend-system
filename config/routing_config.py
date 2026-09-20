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


def _get_unit_interval(key: str, default: float) -> float:
    """[0.0, 1.0] の確率・閾値。NaN / 負値 / 1 超 / 不正 parse は ``default``。"""
    raw = _get_float(key, default)
    if raw != raw or raw < 0.0 or raw > 1.0:
        return default
    return raw


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


# --- Jev (TypeSafe System One) runtime config ---


def jev_model() -> str:
    """Jev model id（既定 jev-latest）。空文字は既定へ戻す。"""
    val = (os.getenv("JEV_MODEL") or "").strip()
    return val or "jev-latest"


def jev_timeout_sec() -> float:
    """Jev HTTP timeout 秒（既定 3.5）。不正値は既定。範囲は 0.5..30 に clamp。"""
    raw = _get_float("JEV_TIMEOUT_SEC", 3.5)
    if raw != raw:  # NaN
        return 3.5
    return max(0.5, min(30.0, raw))


def jev_confidence_floor() -> float:
    """観測用 usable 下限（既定 0.70）。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_CONFIDENCE_FLOOR", 0.70)


def jev_high_confidence() -> float:
    """Phase 2 primary 候補閾値（既定 0.85）。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_HIGH_CONFIDENCE", 0.85)


def jev_noul_threshold() -> float:
    """Noul 観測閾値（既定 0.75）。Phase 1 は観測のみ。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_NOUL_THRESHOLD", 0.75)
