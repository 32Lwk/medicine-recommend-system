"""Phase 4b — PRIMARY / LEGACY_FALLBACK_TRIM 本番デフォルト ON テスト。"""
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
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_DENYLIST", raising=False)


CANARY = "line:canary-test-01"
OTHER = "line:non-canary-test-99"


def test_primary_on_by_default_in_production(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_intent_router_primary_enabled(OTHER) is True


def test_trim_on_by_default_in_production(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_legacy_fallback_trim_enabled(CANARY) is True
    assert is_legacy_fallback_trim_enabled(OTHER) is True


def test_trim_false_when_primary_disabled_sid(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_DENYLIST", OTHER)
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_intent_router_primary_enabled(OTHER) is False
    assert is_legacy_fallback_trim_enabled(OTHER) is False


def test_trim_false_when_global_trim_off(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    monkeypatch.setenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "false")
    assert is_intent_router_primary_enabled(CANARY) is True
    assert is_legacy_fallback_trim_enabled(CANARY) is False


def test_primary_denylist(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
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


def test_primary_explicit_off(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", "false")
    assert is_intent_router_primary_enabled(CANARY) is False
