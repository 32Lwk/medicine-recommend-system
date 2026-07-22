"""CHAT_PIPELINE_V2 フラグ・セッション denylist テスト。"""
from __future__ import annotations

import pytest

from config.llm_flags import (
    is_chat_pipeline_v2_enabled,
    is_chat_pipeline_v2_for_session,
    is_intent_router_dispatch_enabled,
    is_intent_router_llm_enabled,
    is_intent_router_v2_enabled,
)


@pytest.fixture(autouse=True)
def _clear_v2_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_DENYLIST", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM", raising=False)


def test_v2_default_on_outside_pytest(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_chat_pipeline_v2_enabled() is True
    assert is_chat_pipeline_v2_for_session("line:U1") is True


def test_v2_dev_auto_on(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_chat_pipeline_v2_enabled() is True
    assert is_chat_pipeline_v2_for_session("line:U1") is True
    assert is_intent_router_v2_enabled("line:U1") is True
    assert is_intent_router_dispatch_enabled("line:U1") is True
    assert is_intent_router_llm_enabled("line:U1") is True


def test_v2_global_on_cascade_all_subflags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    assert is_chat_pipeline_v2_for_session("line:U1") is True
    assert is_intent_router_v2_enabled("line:U1") is True
    assert is_intent_router_dispatch_enabled("line:U1") is True
    assert is_intent_router_llm_enabled("line:U1") is True


def test_v2_explicit_false(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert is_chat_pipeline_v2_enabled() is False
    assert is_chat_pipeline_v2_for_session("line:U1") is False


def test_v2_denylist_rollback(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_DENYLIST", "line:Ubad")
    assert is_chat_pipeline_v2_for_session("line:Ubad") is False
    assert is_chat_pipeline_v2_for_session("line:Ugood") is True


def test_intent_router_opt_out_dispatch(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH", "false")
    assert is_intent_router_v2_enabled("line:U1") is True
    assert is_intent_router_dispatch_enabled("line:U1") is False
    assert is_intent_router_llm_enabled("line:U1") is True


def test_intent_router_opt_out_router(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "false")
    assert is_intent_router_v2_enabled("line:U1") is False
    assert is_intent_router_dispatch_enabled("line:U1") is False
    assert is_intent_router_llm_enabled("line:U1") is False
