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
#
# Rate/cost/circuit defaults are **conservative candidates** for local/staging.
# They are env-overridable and are NOT Owner-approved production budgets.
# Staging-oriented tiny caps are the code defaults; raise only via env after review.


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


def jev_http_max_retries() -> int:
    """429 / 5xx の最大追加リトライ回数（既定 1、環境変数で 0..2）。

    ``JEV_HTTP_MAX_RETRIES``。timeout / その他 4xx / network はリトライしない。
    """
    return max(0, min(2, _get_int("JEV_HTTP_MAX_RETRIES", 1)))


def jev_retry_jitter_ms() -> tuple[int, int]:
    """Retry sleep jitter range in milliseconds (inclusive).

    ``JEV_RETRY_JITTER_MS_MIN`` / ``JEV_RETRY_JITTER_MS_MAX``（既定 50..150）。
    """
    lo = max(0, _get_int("JEV_RETRY_JITTER_MS_MIN", 50))
    hi = max(lo, _get_int("JEV_RETRY_JITTER_MS_MAX", 150))
    return lo, hi


def jev_confidence_floor() -> float:
    """観測用 usable 下限（既定 0.70）。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_CONFIDENCE_FLOOR", 0.70)


def jev_high_confidence() -> float:
    """Phase 2 primary 候補閾値（既定 0.85）。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_HIGH_CONFIDENCE", 0.85)


def jev_noul_threshold() -> float:
    """Noul 観測閾値（既定 0.75）。Phase 1 は観測のみ。範囲外・負値・不正値は既定。"""
    return _get_unit_interval("JEV_NOUL_THRESHOLD", 0.75)


def jev_max_pending() -> int:
    """Shadow pending soft cap（既定 8）。``JEV_MAX_PENDING`` 0..64。"""
    return max(0, min(64, _get_int("JEV_MAX_PENDING", 8)))


def jev_executor_workers() -> int:
    """Shadow ThreadPoolExecutor workers（既定 2）。``JEV_EXECUTOR_WORKERS`` 1..8。"""
    return max(1, min(8, _get_int("JEV_EXECUTOR_WORKERS", 2)))


def jev_circuit_failure_threshold() -> int:
    """Consecutive failures → open（既定 5）。``JEV_CIRCUIT_FAILURE_THRESHOLD`` 1..50。"""
    return max(1, min(50, _get_int("JEV_CIRCUIT_FAILURE_THRESHOLD", 5)))


def jev_circuit_open_sec() -> float:
    """Open duration seconds（既定 60）。``JEV_CIRCUIT_OPEN_SEC`` 1..3600。"""
    raw = _get_float("JEV_CIRCUIT_OPEN_SEC", 60.0)
    if raw != raw:
        return 60.0
    return max(1.0, min(3600.0, raw))


def jev_circuit_half_open_probes() -> int:
    """Half-open concurrent probes（既定 1）。``JEV_CIRCUIT_HALF_OPEN_PROBES`` 1..5。"""
    return max(1, min(5, _get_int("JEV_CIRCUIT_HALF_OPEN_PROBES", 1)))


def jev_rate_rpm() -> int:
    """Requests/minute candidate cap（既定 10 staging-tiny）。0=disabled。"""
    return max(0, _get_int("JEV_RATE_RPM", 10))


def jev_rate_rph() -> int:
    """Requests/hour candidate cap（既定 60）。0=disabled。"""
    return max(0, _get_int("JEV_RATE_RPH", 60))


def jev_rate_rpd() -> int:
    """Requests/day candidate cap（既定 200, ~24h sliding）。0=disabled。"""
    return max(0, _get_int("JEV_RATE_RPD", 200))


def jev_tokens_per_request_max() -> int:
    """Per-request input token soft flag（既定 4000）。0=disabled。"""
    return max(0, _get_int("JEV_TOKENS_PER_REQUEST_MAX", 4000))


def jev_tokens_day_max() -> int:
    """UTC-day input token candidate cap（既定 100000）。0=disabled。"""
    return max(0, _get_int("JEV_TOKENS_DAY_MAX", 100_000))


def jev_est_cost_usd_day_max() -> float:
    """Estimated USD/day candidate cap（既定 1.0）。**推定のみ・Owner 承認予算ではない**。

    ``JEV_EST_COST_USD_DAY_MAX``。0=disabled。
    """
    raw = _get_float("JEV_EST_COST_USD_DAY_MAX", 1.0)
    if raw != raw or raw < 0.0:
        return 1.0
    return raw


def jev_shadow_emergency_disable() -> bool:
    """Emergency shadow drop（``JEV_SHADOW_EMERGENCY_DISABLE``）。明示 true のみ。"""
    val = (os.getenv("JEV_SHADOW_EMERGENCY_DISABLE") or "").strip().lower()
    return val in ("1", "true", "yes", "on")


def jev_cost_guard_enabled() -> bool:
    """When false, rate/cost windows are not enforced（circuit still applies）。

    ``JEV_COST_GUARD_ENABLED`` 既定 true（未設定=ON）。明示 false で無効。
    """
    val = os.getenv("JEV_COST_GUARD_ENABLED")
    if val is None or not str(val).strip():
        return True
    return str(val).strip().lower() not in ("0", "false", "no", "off")

