"""AgentDispatcher テスト（Wave 1b dispatch）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dialogue.dispatcher import (
    _apply_decision_to_context,
    try_agent_dispatch,
)
from src.dialogue.routing.types import RouteDecision


@pytest.fixture
def ctx():
    session: dict = {
        "messages": [],
        "_intent_router_shadow": {
            "primary_route": "Physical",
            "sub_route": "rule_based_recommend",
            "confidence": 0.9,
            "resolved_by": "gate",
            "source": "symptom_signal",
        },
    }
    mock_ctx = MagicMock()
    mock_ctx.session = session
    mock_ctx.sid = "line:U1"
    mock_ctx.user_message = "頭痛い"
    mock_ctx.sanitized_message = "頭痛い"
    mock_ctx.processed_message = "頭痛い"
    mock_ctx.original_user_message = "頭痛い"
    mock_ctx.triage_result = {"category": "Physical", "confidence": 0.9}
    mock_ctx.inappropriate_request_detected = False
    mock_ctx.recommendation_client = MagicMock()
    mock_ctx.client_info = MagicMock()
    mock_ctx.user_agent = "test"
    mock_ctx.client_ip = "127.0.0.1"
    mock_ctx.trace_id = "trace-1"
    mock_ctx.routing = None
    return mock_ctx


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=False)
def test_dispatch_skipped_when_flag_off(_enabled, ctx):
    assert try_agent_dispatch(ctx, None) is None


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=True)
@patch("src.dialogue.dispatcher._dispatch_physical")
def test_dispatch_physical(mock_physical, _enabled, ctx):
    mock_physical.return_value = ({"status": "ok"}, 200)
    resp = try_agent_dispatch(ctx, MagicMock())
    assert resp == ({"status": "ok"}, 200)
    assert ctx.session["_intent_router_dispatch"]["handler"] == "physical_agent"
    assert ctx.triage_result["category"] == "Physical"
    assert ctx.session["dialogue_state"]["routing"]["dispatched"] is True


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=True)
def test_dispatch_unknown_falls_back(_enabled, ctx):
    ctx.session["_intent_router_shadow"]["primary_route"] = "Unknown"
    ctx.session["_intent_router_shadow"]["sub_route"] = "clarification"
    assert try_agent_dispatch(ctx, None) is None


def test_apply_decision_concierge_intent(ctx):
    decision = RouteDecision(
        primary_route="Concierge",
        sub_route="architecture",
        confidence=0.95,
        resolved_by="gate",
    )
    _apply_decision_to_context(ctx, decision)
    assert ctx.triage_result["category"] == "Other"
    assert ctx.triage_result["concierge_intent"] == "architecture"


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=True)
@patch("src.dialogue.dispatcher._dispatch_emergency")
def test_dispatch_emergency(mock_emergency, _enabled, ctx):
    ctx.session["_intent_router_shadow"] = {
        "primary_route": "Emergency",
        "sub_route": "emergency_dispatch",
        "confidence": 0.95,
        "resolved_by": "gate",
        "source": "triage_emergency",
    }
    mock_emergency.return_value = ({"status": "ok"}, 200)
    resp = try_agent_dispatch(ctx, None)
    assert resp == ({"status": "ok"}, 200)
    assert ctx.triage_result["category"] == "Emergency"


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=True)
@patch("src.dialogue.dispatcher._dispatch_physical")
def test_dispatch_physical_clears_pending_cancel_flag(mock_physical, _enabled, ctx, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    mock_physical.return_value = ({"status": "ok"}, 200)
    ctx.session["dialogue_state"] = {
        "version": 1,
        "flags": {"pending_cancelled_by_physical": True},
    }
    try_agent_dispatch(ctx, MagicMock())
    assert "pending_cancelled_by_physical" not in ctx.session["dialogue_state"]["flags"]
