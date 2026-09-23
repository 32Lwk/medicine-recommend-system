"""Unit tests for Jev shadow circuit / rate / cost guards."""
from __future__ import annotations

import time

from src.dialogue.routing.jev_shadow_guards import (
    JevShadowGuards,
    ShadowGuardConfig,
    reset_shadow_guards_for_tests,
)


def test_queue_full_blocks():
    g = JevShadowGuards(ShadowGuardConfig(max_pending=2))
    d = g.check_admit(pending_count=2)
    assert d.allow is False
    assert d.reason == "queue_full"


def test_circuit_opens_after_consecutive_failures():
    g = JevShadowGuards(ShadowGuardConfig(consecutive_failure_open=3, open_duration_s=30.0))
    assert g.check_admit(pending_count=0).allow is True
    g.record_failure()
    g.record_failure()
    g.record_failure()
    d = g.check_admit(pending_count=0)
    assert d.allow is False
    assert d.circuit_state == "open"
    assert d.reason == "circuit_open"


def test_manual_kill_blocks():
    g = JevShadowGuards()
    g.force_open()
    d = g.check_admit(pending_count=0)
    assert d.allow is False
    assert d.reason == "circuit_open_manual"
    g.force_close()
    assert g.check_admit(pending_count=0).allow is True


def test_rpm_and_cost_guards():
    g = JevShadowGuards(
        ShadowGuardConfig(rpm=2, rph=100, rpd=100, max_est_cost_usd_day=0.000001, usd_per_mtok_input=1.0)
    )
    assert g.check_admit(pending_count=0).allow is True
    g.record_scheduled()
    assert g.check_admit(pending_count=0).allow is True
    g.record_scheduled()
    d = g.check_admit(pending_count=0)
    assert d.allow is False
    assert d.reason == "rate_rpm"

    g2 = JevShadowGuards(
        ShadowGuardConfig(
            rpm=100, max_est_cost_usd_day=0.0000001, usd_per_mtok_input=1.0
        )
    )
    d2 = g2.check_admit(pending_count=0, est_tokens=10)
    assert d2.allow is False
    assert d2.reason == "cost_day_estimate"


def test_success_resets_circuit():
    reset_shadow_guards_for_tests()
    g = JevShadowGuards(ShadowGuardConfig(consecutive_failure_open=2, open_duration_s=60))
    g.record_failure()
    g.record_failure()
    assert g.check_admit(pending_count=0).allow is False
    g.force_close()
    g.record_success(tokens=10)
    assert g.check_admit(pending_count=0).allow is True
    assert g.snapshot_metrics()["tokens_day"] >= 10


def test_half_open_allows_single_probe_then_reopens_on_failure():
    g = JevShadowGuards(
        ShadowGuardConfig(
            consecutive_failure_open=1,
            open_duration_s=0.01,
            half_open_max_probes=1,
        )
    )
    g.record_failure()
    assert g.check_admit(pending_count=0).allow is False
    time.sleep(0.02)
    # half-open: one probe
    d1 = g.check_admit(pending_count=0)
    assert d1.allow is True
    assert d1.circuit_state == "half_open"
    d2 = g.check_admit(pending_count=0)
    assert d2.allow is False
    assert d2.reason == "circuit_half_open_saturated"
    g.record_failure()
    assert g.circuit_state() == "open"


def test_emergency_disable_blocks(monkeypatch):
    monkeypatch.setenv("JEV_SHADOW_EMERGENCY_DISABLE", "true")
    reset_shadow_guards_for_tests()
    g = JevShadowGuards(ShadowGuardConfig())
    d = g.check_admit(pending_count=0)
    assert d.allow is False
    assert d.reason == "emergency_disable"
    monkeypatch.delenv("JEV_SHADOW_EMERGENCY_DISABLE", raising=False)
    reset_shadow_guards_for_tests()
