"""Unified router — medicine_qa layer1 テスト。"""
from __future__ import annotations

import pytest

from src.dialogue.routing.unified_router import resolve_unified_route


@pytest.fixture(autouse=True)
def _enable_v2(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def test_layer1_routes_comparison_to_medicine_qa():
    session = {"messages": []}
    decision = resolve_unified_route(
        "ロキソニンとイブの違いって何？",
        session,
        "sid",
        triage_result={"category": "Ask"},
    )
    assert decision.sub_route == "medicine_qa"
    assert decision.execution_lock is True
    assert decision.layer_used == "layer1"


def test_layer1_side_effect_still_locked():
    session = {"messages": []}
    decision = resolve_unified_route(
        "ロキソニンって眠くなる？",
        session,
        "sid",
        triage_result={"category": "Ask"},
    )
    assert decision.sub_route == "medicine_side_effect_qa"
    assert decision.execution_lock is True
