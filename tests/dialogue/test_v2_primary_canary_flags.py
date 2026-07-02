"""Phase 4b-5b — production PRIMARY_ALLOWLIST / LEGACY_FALLBACK_TRIM テスト。"""
from __future__ import annotations

import pytest

from config.llm_flags import (
    is_intent_router_primary_enabled,
    is_legacy_fallback_trim_enabled,
)


@pytest.fixture(autouse=True)
def _prod_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", "true")
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_DENYLIST", raising=False)


CANARY = "line:canary-test-01"
OTHER = "line:non-canary-test-99"


def test_primary_off_outside_allowlist_in_production(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", CANARY)
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_intent_router_primary_enabled(OTHER) is False


def test_primary_off_when_allowlist_empty_in_production(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", raising=False)
    assert is_intent_router_primary_enabled(CANARY) is False
    assert is_intent_router_primary_enabled(OTHER) is False


def test_trim_follows_primary_in_production(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "true")
    assert is_legacy_fallback_trim_enabled(CANARY) is True
    assert is_legacy_fallback_trim_enabled(OTHER) is False


def test_trim_false_when_primary_disabled_sid(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", f"{CANARY},{OTHER}")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "true")
    assert is_legacy_fallback_trim_enabled(OTHER) is False


def test_trim_false_when_global_trim_off(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "false")
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_legacy_fallback_trim_enabled(CANARY) is False


def test_primary_denylist_overrides_allowlist(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", CANARY)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_DENYLIST", CANARY)
    assert is_intent_router_primary_enabled(CANARY) is False


def test_primary_auto_on_in_development_without_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", raising=False)
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_legacy_fallback_trim_enabled(CANARY) is True


def test_primary_stays_off_in_production_without_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", raising=False)
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_intent_router_primary_enabled(CANARY) is False
