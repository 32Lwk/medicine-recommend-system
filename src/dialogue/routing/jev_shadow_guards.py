"""Jev shadow circuit breaker, rate and cost guards (fail-open for user path).

Conservative **candidate** defaults for local/staging (tiny caps). Override via
``config.routing_config`` env vars (``JEV_*``) or legacy ``JEV_SHADOW_*`` aliases.
Does **not** mutate user response / Safety / SessionOps / executed routes.

Estimated USD caps are **not** Owner-approved production budgets.
Cost estimation basis aligns with ``jev_metrics.JEV_INPUT_COST_USD_PER_MTOK``.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

# Align estimate basis with jev_metrics (input-only estimate; not invoice).
_DEFAULT_USD_PER_MTOK = 0.042


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _first_env_int(*names: str, default: int) -> int:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and str(raw).strip() != "":
            return _env_int(name, default)
    return default


def _first_env_float(*names: str, default: float) -> float:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and str(raw).strip() != "":
            return _env_float(name, default)
    return default


@dataclass(frozen=True)
class ShadowGuardConfig:
    """Candidate caps — staging-tiny by default; env-overridable."""

    max_pending: int = 8
    concurrency: int = 2
    request_timeout_s: float = 3.5
    max_retries: int = 1
    consecutive_failure_open: int = 5
    open_duration_s: float = 60.0
    half_open_max_probes: int = 1
    rpm: int = 10
    rph: int = 60
    rpd: int = 200
    max_tokens_per_request: int = 4000
    max_tokens_day: int = 100_000
    # Estimated USD/day soft trip (candidate; Owner must approve production)
    max_est_cost_usd_day: float = 1.0
    usd_per_mtok_input: float = _DEFAULT_USD_PER_MTOK
    cost_guard_enabled: bool = True


def load_shadow_guard_config() -> ShadowGuardConfig:
    """Load from routing_config when available; else env with staging-tiny defaults."""
    try:
        from config.routing_config import (
            jev_circuit_failure_threshold,
            jev_circuit_half_open_probes,
            jev_circuit_open_sec,
            jev_cost_guard_enabled,
            jev_est_cost_usd_day_max,
            jev_executor_workers,
            jev_http_max_retries,
            jev_max_pending,
            jev_rate_rpd,
            jev_rate_rph,
            jev_rate_rpm,
            jev_timeout_sec,
            jev_tokens_day_max,
            jev_tokens_per_request_max,
        )

        return ShadowGuardConfig(
            max_pending=int(jev_max_pending()),
            concurrency=int(jev_executor_workers()),
            request_timeout_s=float(jev_timeout_sec()),
            max_retries=int(jev_http_max_retries()),
            consecutive_failure_open=int(jev_circuit_failure_threshold()),
            open_duration_s=float(jev_circuit_open_sec()),
            half_open_max_probes=int(jev_circuit_half_open_probes()),
            rpm=int(jev_rate_rpm()),
            rph=int(jev_rate_rph()),
            rpd=int(jev_rate_rpd()),
            max_tokens_per_request=int(jev_tokens_per_request_max()),
            max_tokens_day=int(jev_tokens_day_max()),
            max_est_cost_usd_day=float(jev_est_cost_usd_day_max()),
            usd_per_mtok_input=_first_env_float(
                "JEV_SHADOW_USD_PER_MTOK",
                "JEV_INPUT_COST_USD_PER_MTOK",
                default=_DEFAULT_USD_PER_MTOK,
            ),
            cost_guard_enabled=bool(jev_cost_guard_enabled()),
        )
    except Exception:
        return ShadowGuardConfig(
            max_pending=_first_env_int("JEV_MAX_PENDING", "JEV_SHADOW_MAX_PENDING", default=8),
            concurrency=_first_env_int(
                "JEV_EXECUTOR_WORKERS", "JEV_SHADOW_CONCURRENCY", default=2
            ),
            request_timeout_s=_first_env_float(
                "JEV_TIMEOUT_SEC", "JEV_SHADOW_TIMEOUT_S", default=3.5
            ),
            max_retries=_first_env_int(
                "JEV_HTTP_MAX_RETRIES", "JEV_SHADOW_MAX_RETRIES", default=1
            ),
            consecutive_failure_open=_first_env_int(
                "JEV_CIRCUIT_FAILURE_THRESHOLD", "JEV_SHADOW_CB_FAILURES", default=5
            ),
            open_duration_s=_first_env_float(
                "JEV_CIRCUIT_OPEN_SEC", "JEV_SHADOW_CB_OPEN_S", default=60.0
            ),
            half_open_max_probes=_first_env_int(
                "JEV_CIRCUIT_HALF_OPEN_PROBES",
                "JEV_SHADOW_CB_HALF_OPEN_PROBES",
                default=1,
            ),
            rpm=_first_env_int("JEV_RATE_RPM", "JEV_SHADOW_RPM", default=10),
            rph=_first_env_int("JEV_RATE_RPH", "JEV_SHADOW_RPH", default=60),
            rpd=_first_env_int("JEV_RATE_RPD", "JEV_SHADOW_RPD", default=200),
            max_tokens_per_request=_first_env_int(
                "JEV_TOKENS_PER_REQUEST_MAX", "JEV_SHADOW_MAX_TOKENS_REQ", default=4000
            ),
            max_tokens_day=_first_env_int(
                "JEV_TOKENS_DAY_MAX", "JEV_SHADOW_MAX_TOKENS_DAY", default=100_000
            ),
            max_est_cost_usd_day=_first_env_float(
                "JEV_EST_COST_USD_DAY_MAX", "JEV_SHADOW_MAX_COST_USD_DAY", default=1.0
            ),
            usd_per_mtok_input=_first_env_float(
                "JEV_SHADOW_USD_PER_MTOK",
                "JEV_INPUT_COST_USD_PER_MTOK",
                default=_DEFAULT_USD_PER_MTOK,
            ),
            cost_guard_enabled=True,
        )


def _emergency_disable() -> bool:
    try:
        from config.routing_config import jev_shadow_emergency_disable

        return bool(jev_shadow_emergency_disable())
    except Exception:
        val = (os.getenv("JEV_SHADOW_EMERGENCY_DISABLE") or "").strip().lower()
        return val in ("1", "true", "yes", "on")


@dataclass
class GuardDecision:
    allow: bool
    reason: str
    circuit_state: str


class JevShadowGuards:
    """Process-local guards for shadow scheduling only."""

    def __init__(self, config: Optional[ShadowGuardConfig] = None) -> None:
        self.config = config or load_shadow_guard_config()
        self._lock = threading.Lock()
        self._consecutive_failures = 0
        self._circuit_opened_at: float | None = None
        self._half_open_probes = 0
        self._req_timestamps: list[float] = []
        self._tokens_day = 0
        self._tokens_day_epoch = self._day_key()
        self._est_cost_usd_day = 0.0
        self._manual_open = False

    @staticmethod
    def _day_key() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _roll_day(self) -> None:
        key = self._day_key()
        if key != self._tokens_day_epoch:
            self._tokens_day_epoch = key
            self._tokens_day = 0
            self._est_cost_usd_day = 0.0
            self._req_timestamps = []

    def circuit_state(self) -> str:
        with self._lock:
            return self._circuit_state_unlocked(time.monotonic())

    def _circuit_state_unlocked(self, now: float) -> str:
        if self._manual_open:
            return "open_manual"
        if self._circuit_opened_at is None:
            return "closed"
        elapsed = now - self._circuit_opened_at
        if elapsed >= self.config.open_duration_s:
            return "half_open"
        return "open"

    def force_open(self) -> None:
        with self._lock:
            self._manual_open = True
            self._circuit_opened_at = time.monotonic()

    def force_close(self) -> None:
        with self._lock:
            self._manual_open = False
            self._circuit_opened_at = None
            self._consecutive_failures = 0
            self._half_open_probes = 0

    def reset_for_tests(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._circuit_opened_at = None
            self._half_open_probes = 0
            self._req_timestamps = []
            self._tokens_day = 0
            self._est_cost_usd_day = 0.0
            self._manual_open = False
            self._tokens_day_epoch = self._day_key()

    def check_admit(self, *, pending_count: int, est_tokens: int = 0) -> GuardDecision:
        """Return whether a new shadow attempt may be scheduled."""
        with self._lock:
            now = time.monotonic()
            self._roll_day()
            state = self._circuit_state_unlocked(now)

            if _emergency_disable():
                return GuardDecision(False, "emergency_disable", state)

            if state == "open_manual":
                return GuardDecision(False, "circuit_open_manual", state)
            if state == "open":
                return GuardDecision(False, "circuit_open", state)
            if state == "half_open":
                if self._half_open_probes >= self.config.half_open_max_probes:
                    return GuardDecision(False, "circuit_half_open_saturated", state)

            if pending_count >= self.config.max_pending:
                return GuardDecision(False, "queue_full", state)

            if self.config.cost_guard_enabled:
                window_ts = [t for t in self._req_timestamps if now - t < 86400.0]
                self._req_timestamps = window_ts
                rpm = sum(1 for t in window_ts if now - t < 60.0)
                rph = sum(1 for t in window_ts if now - t < 3600.0)
                rpd = len(window_ts)
                if self.config.rpm > 0 and rpm >= self.config.rpm:
                    return GuardDecision(False, "rate_rpm", state)
                if self.config.rph > 0 and rph >= self.config.rph:
                    return GuardDecision(False, "rate_rph", state)
                if self.config.rpd > 0 and rpd >= self.config.rpd:
                    return GuardDecision(False, "rate_rpd", state)

                if (
                    self.config.max_tokens_per_request > 0
                    and est_tokens > self.config.max_tokens_per_request
                ):
                    return GuardDecision(False, "tokens_per_request", state)
                if (
                    self.config.max_tokens_day > 0
                    and self._tokens_day + max(0, est_tokens) > self.config.max_tokens_day
                ):
                    return GuardDecision(False, "tokens_day", state)

                est_cost = (
                    max(0, est_tokens) / 1_000_000.0
                ) * self.config.usd_per_mtok_input
                # max==0 means hard block any positive estimated spend
                if self._est_cost_usd_day + est_cost > self.config.max_est_cost_usd_day:
                    return GuardDecision(False, "cost_day_estimate", state)

            if state == "half_open":
                self._half_open_probes += 1

            return GuardDecision(True, "ok", state)

    def record_scheduled(self) -> None:
        with self._lock:
            self._req_timestamps.append(time.monotonic())

    def record_success(self, *, tokens: int = 0) -> None:
        with self._lock:
            self._roll_day()
            self._consecutive_failures = 0
            self._circuit_opened_at = None
            self._half_open_probes = 0
            self._manual_open = False
            tok = max(0, int(tokens))
            self._tokens_day += tok
            self._est_cost_usd_day += (tok / 1_000_000.0) * self.config.usd_per_mtok_input

    def record_failure(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._consecutive_failures += 1
            state = self._circuit_state_unlocked(now)
            if state == "half_open":
                self._circuit_opened_at = now
                self._half_open_probes = 0
                return
            if self._consecutive_failures >= self.config.consecutive_failure_open:
                self._circuit_opened_at = now
                self._half_open_probes = 0

    def snapshot_metrics(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            self._roll_day()
            window_ts = [t for t in self._req_timestamps if now - t < 86400.0]
            return {
                "circuit_state": self._circuit_state_unlocked(now),
                "consecutive_failures": self._consecutive_failures,
                "tokens_day": self._tokens_day,
                "est_cost_usd_day": round(self._est_cost_usd_day, 6),
                "requests_last_60s": sum(1 for t in window_ts if now - t < 60.0),
                "requests_last_1h": sum(1 for t in window_ts if now - t < 3600.0),
                "requests_last_24h": len(window_ts),
                "manual_open": self._manual_open,
                "emergency_disable": _emergency_disable(),
                "limits": {
                    "max_pending": self.config.max_pending,
                    "concurrency": self.config.concurrency,
                    "rpm": self.config.rpm,
                    "rph": self.config.rph,
                    "rpd": self.config.rpd,
                    "tokens_day": self.config.max_tokens_day,
                    "est_cost_usd_day": self.config.max_est_cost_usd_day,
                    "basis": "conservative_candidate_defaults_env_overridable",
                },
            }


_GUARDS: Optional[JevShadowGuards] = None
_GUARDS_LOCK = threading.Lock()


def get_shadow_guards() -> JevShadowGuards:
    global _GUARDS
    with _GUARDS_LOCK:
        if _GUARDS is None:
            _GUARDS = JevShadowGuards()
        return _GUARDS


def reset_shadow_guards_for_tests() -> None:
    g = get_shadow_guards()
    g.reset_for_tests()
    g.config = load_shadow_guard_config()


__all__ = [
    "GuardDecision",
    "JevShadowGuards",
    "ShadowGuardConfig",
    "get_shadow_guards",
    "load_shadow_guard_config",
    "reset_shadow_guards_for_tests",
]
