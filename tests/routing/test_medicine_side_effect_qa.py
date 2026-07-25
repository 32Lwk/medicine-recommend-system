"""medicine_side_effect_qa ルーティング regression tests。"""
from __future__ import annotations

import pytest

from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.unified_router import resolve_unified_route
from src.services.medicine_side_effect_routing import (
    is_medicine_side_effect_route,
    mentions_drowsiness_side_effect,
)


@pytest.fixture(autouse=True)
def _enable_side_effect_flags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def test_loxoprofen_drowsiness_is_side_effect_route():
    msg = "ロキソニンって眠い？"
    assert is_medicine_side_effect_route(msg)
    assert mentions_drowsiness_side_effect(msg)


def test_gate_routes_side_effect_qa_without_reco_history():
    session = {"messages": []}
    decision = run_deterministic_gate("ロキソニンって眠い？", session, "sid")
    assert decision is not None
    assert decision.primary_route == "Physical"
    assert decision.sub_route == "medicine_side_effect_qa"


def test_unified_router_layer1_side_effect():
    session = {"messages": []}
    decision = resolve_unified_route(
        "ロキソニンって眠くなる？",
        session,
        "sid",
        triage_result={"category": "Ask"},
    )
    assert decision.sub_route == "medicine_side_effect_qa"
    assert decision.execution_lock is True
    assert decision.layer_used == "layer1"


def test_symptom_drowsiness_not_side_effect_route():
    assert not is_medicine_side_effect_route("眠い")
    assert not is_medicine_side_effect_route("最近眠くてつらい")
