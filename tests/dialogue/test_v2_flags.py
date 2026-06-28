"""CHAT_PIPELINE_V2 フラグ・セッション allowlist テスト。"""
from __future__ import annotations

import os

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
    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_ALLOWLIST", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_DENYLIST", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH", raising=False)
    monkeypatch.delenv("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM", raising=False)


def test_v2_default_off():
    assert is_chat_pipeline_v2_enabled() is False
    assert is_chat_pipeline_v2_for_session("line:U1") is False


def test_v2_global_on(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    assert is_chat_pipeline_v2_for_session("line:U1") is True


def test_v2_allowlist_canary(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_ALLOWLIST", "line:Ucanary")
    assert is_chat_pipeline_v2_for_session("line:Ucanary") is True
    assert is_chat_pipeline_v2_for_session("line:Uother") is False


def test_v2_denylist_rollback(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_DENYLIST", "line:Ubad")
    assert is_chat_pipeline_v2_for_session("line:Ubad") is False
    assert is_chat_pipeline_v2_for_session("line:Ugood") is True


def test_intent_router_dispatch_requires_router(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH", "true")
    assert is_intent_router_dispatch_enabled("line:U1") is False

    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    assert is_intent_router_v2_enabled("line:U1") is True
    assert is_intent_router_dispatch_enabled("line:U1") is True


def test_intent_router_llm_requires_router(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM", "true")
    assert is_intent_router_llm_enabled("line:U1") is False

    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    assert is_intent_router_llm_enabled("line:U1") is True
