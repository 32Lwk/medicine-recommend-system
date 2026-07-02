"""UX品質改善 Phase 2–3 フラグ — 開発ランタイム自動 ON。"""
from __future__ import annotations

import pytest

from config.llm_flags import (
    is_concierge_followup_routing_enabled,
    is_concierge_intent_routing_enabled,
    is_counseling_context_maintain_enabled,
    is_counseling_tone_variety_enabled,
    is_emergency_channel_split_enabled,
    is_low_risk_headache_reco_enabled,
    is_store_procurement_routing_enabled,
    is_ux_correction_delete_cancel_enabled,
    is_ux_progressive_clarification_enabled,
    is_ux_reco_dedup_enabled,
    is_ux_session_ops_real_data_enabled,
    is_violence_context_guard_enabled,
)

UX_FLAG_ENV_NAMES = (
    "SAFETY_VIOLENCE_CONTEXT_GUARD",
    "SAFETY_EMERGENCY_CHANNEL_SPLIT",
    "UX_COUNSELING_CONTEXT_MAINTAIN",
    "UX_COUNSELING_TONE_VARIETY",
    "ROUTING_CONCIERGE_INTENT",
    "ROUTING_CONCIERGE_FOLLOWUP",
    "ROUTING_STORE_PROCUREMENT",
    "RECO_LOW_RISK_HEADACHE",
    "UX_CORRECTION_DELETE_CANCEL",
    "UX_SESSION_OPS_REAL_DATA",
    "UX_PROGRESSIVE_CLARIFICATION",
    "UX_RECO_DEDUP",
)

UX_FLAGS = (
    is_violence_context_guard_enabled,
    is_emergency_channel_split_enabled,
    is_counseling_context_maintain_enabled,
    is_counseling_tone_variety_enabled,
    is_concierge_intent_routing_enabled,
    is_concierge_followup_routing_enabled,
    is_store_procurement_routing_enabled,
    is_low_risk_headache_reco_enabled,
    is_ux_correction_delete_cancel_enabled,
    is_ux_session_ops_real_data_enabled,
    is_ux_progressive_clarification_enabled,
    is_ux_reco_dedup_enabled,
)


@pytest.fixture(autouse=True)
def _clear_ux_flag_env(monkeypatch):
    for name in UX_FLAG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("checker", UX_FLAGS, ids=[f.__name__ for f in UX_FLAGS])
def test_ux_flags_auto_on_in_development(monkeypatch, checker):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is True


@pytest.mark.parametrize("checker", UX_FLAGS, ids=[f.__name__ for f in UX_FLAGS])
def test_ux_flags_off_in_production_without_env(monkeypatch, checker):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is False


def test_ux_flags_explicit_false_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_violence_context_guard_enabled() is False
