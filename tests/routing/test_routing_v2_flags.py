"""Routing v2 サブフラグ — カナリアなし一括 ON テスト。"""
from __future__ import annotations

import pytest

from config import llm_flags


@pytest.fixture(autouse=True)
def _v2_on(monkeypatch):
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")


def test_routing_flags_default_on_with_v2():
    assert llm_flags.is_unified_router_enabled("sid") is True
    assert llm_flags.is_medicine_side_effect_qa_enabled("sid") is True
    assert llm_flags.is_routing_followup_llm_enabled("sid") is True
    assert llm_flags.is_meta_safety_shortpath_enabled() is True
    assert llm_flags.is_medicine_side_effect_kb_enabled() is True


def test_routing_flags_explicit_false_rollback(monkeypatch):
    monkeypatch.setenv("ROUTING_UNIFIED_PIPELINE", "false")
    monkeypatch.setenv("ROUTING_MEDICINE_SIDE_EFFECT_QA", "false")
    assert llm_flags.is_unified_router_enabled("sid") is False
    assert llm_flags.is_medicine_side_effect_qa_enabled("sid") is False


def test_routing_flags_off_when_v2_disabled(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "false")
    assert llm_flags.is_unified_router_enabled("sid") is False
    assert llm_flags.is_medicine_side_effect_qa_enabled("sid") is False
