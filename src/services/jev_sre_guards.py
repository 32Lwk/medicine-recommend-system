"""Compatibility facade: Jev SRE guards live in ``jev_shadow_guards``.

Prefer importing from ``src.dialogue.routing.jev_shadow_guards``.
This module re-exports helpers for services-layer / observability callers.
"""
from __future__ import annotations

from src.dialogue.routing.jev_shadow_guards import (
    GuardDecision,
    JevShadowGuards,
    ShadowGuardConfig,
    get_shadow_guards,
    load_shadow_guard_config,
    reset_shadow_guards_for_tests,
)

# Aliases matching earlier Worker E draft API
reset_guards_for_tests = reset_shadow_guards_for_tests

SKIP_CIRCUIT_OPEN = "circuit_open"
SKIP_COST_DAY = "cost_day_estimate"
SKIP_EMERGENCY = "emergency_disable"
SKIP_RATE_RPD = "rate_rpd"
SKIP_RATE_RPH = "rate_rph"
SKIP_RATE_RPM = "rate_rpm"
SKIP_TOKENS_DAY = "tokens_day"
SKIP_TOKENS_REQUEST = "tokens_per_request"


def circuit_snapshot():
    g = get_shadow_guards()
    snap = g.snapshot_metrics()
    return snap


def observability_bundle(*, queue_depth: int = 0) -> dict:
    g = get_shadow_guards()
    snap = g.snapshot_metrics()
    return {
        "circuit": {
            "state": snap.get("circuit_state"),
            "consecutive_failures": snap.get("consecutive_failures"),
            "manual_open": snap.get("manual_open"),
            "emergency_disable": snap.get("emergency_disable"),
        },
        "queue": {
            "pending": queue_depth,
            "max_pending": (snap.get("limits") or {}).get("max_pending"),
            "workers": (snap.get("limits") or {}).get("concurrency"),
        },
        "rate_cost": {
            "rpm_used": snap.get("requests_last_60s"),
            "rph_used": snap.get("requests_last_1h"),
            "rpd_used": snap.get("requests_last_24h"),
            "tokens_day_used": snap.get("tokens_day"),
            "cost_day_estimate_usd": snap.get("est_cost_usd_day"),
            "limits": snap.get("limits"),
        },
    }


def allow_shadow_call(*, queue_depth: int = 0, est_tokens: int = 0) -> GuardDecision:
    return get_shadow_guards().check_admit(
        pending_count=queue_depth, est_tokens=est_tokens
    )


__all__ = [
    "GuardDecision",
    "JevShadowGuards",
    "SKIP_CIRCUIT_OPEN",
    "SKIP_COST_DAY",
    "SKIP_EMERGENCY",
    "SKIP_RATE_RPD",
    "SKIP_RATE_RPH",
    "SKIP_RATE_RPM",
    "SKIP_TOKENS_DAY",
    "SKIP_TOKENS_REQUEST",
    "ShadowGuardConfig",
    "allow_shadow_call",
    "circuit_snapshot",
    "get_shadow_guards",
    "load_shadow_guard_config",
    "observability_bundle",
    "reset_guards_for_tests",
    "reset_shadow_guards_for_tests",
]
