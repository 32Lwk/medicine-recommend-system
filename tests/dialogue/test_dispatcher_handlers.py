"""Phase 4a-2: dispatch handler が None を返す回帰の修正テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dialogue.dispatcher import (
    _apply_decision_to_context,
    _dispatch_session_ops,
    try_agent_dispatch,
)
from src.dialogue.routing.types import RouteDecision
from src.services.concierge_orchestrator import resolve_intent_from_triage


@pytest.fixture
def ctx():
    session: dict = {"messages": []}
    mock_ctx = MagicMock()
    mock_ctx.session = session
    mock_ctx.sid = "web:test"
    mock_ctx.user_message = "テスト"
    mock_ctx.sanitized_message = "テスト"
    mock_ctx.triage_result = {"category": "Other", "subcategory": "general_other"}
    mock_ctx.recommendation_client = MagicMock()
    return mock_ctx


def test_resolve_intent_general_other_with_router_dispatch():
    triage = {
        "concierge_intent": "general_other",
        "category": "Other",
        "_intent_router_dispatch": True,
    }
    intent = resolve_intent_from_triage(
        triage,
        {},
        "このサービスで何ができますか？",
    )
    assert intent is not None
    assert intent in ("capabilities", "redirect", "greeting", "app_about")


def test_resolve_intent_general_other_without_dispatch_returns_none():
    triage = {"concierge_intent": "general_other", "category": "Other"}
    assert (
        resolve_intent_from_triage(triage, {}, "こんにちは") is None
    )


def test_apply_decision_store_overrides_general_other_subcategory(ctx):
    decision = RouteDecision(
        primary_route="Store",
        sub_route="store_locator",
        confidence=0.9,
        resolved_by="gate",
    )
    _apply_decision_to_context(ctx, decision)
    assert ctx.triage_result["subcategory"] == "store_inquiry"
    assert ctx.triage_result["_intent_router_dispatch"] is True


def test_apply_decision_session_ops_pending_clear_alias(ctx):
    decision = RouteDecision(
        primary_route="SessionOps",
        sub_route="cancel",
        confidence=0.9,
        resolved_by="gate",
    )
    _apply_decision_to_context(ctx, decision)
    assert ctx.triage_result["session_intent"] == "pending_clear"


@patch("src.dialogue.session_ops.try_handle_session_ops")
def test_dispatch_session_ops_calls_try_handle_session_ops(mock_ops, ctx):
    mock_ops.return_value = ({"status": "ok"}, 200)
    ctx.sanitized_message = "記憶を消して"
    resp = _dispatch_session_ops(ctx)
    assert resp == ({"status": "ok"}, 200)
    mock_ops.assert_called_once()


@patch("src.dialogue.dispatcher.is_intent_router_dispatch_enabled", return_value=True)
@patch("src.dialogue.dispatcher._dispatch_concierge")
def test_dispatch_concierge_general_other(mock_concierge, _enabled, ctx):
    ctx.session["_intent_router_shadow"] = {
        "primary_route": "Concierge",
        "sub_route": "general_other",
        "confidence": 0.9,
        "resolved_by": "gate",
        "source": "meta_probe",
    }
    mock_concierge.return_value = ({"status": "ok"}, 200)
    resp = try_agent_dispatch(ctx, MagicMock())
    assert resp == ({"status": "ok"}, 200)
    assert ctx.triage_result["concierge_intent"] == "general_other"


@patch("src.services.store_inquiry_handler.should_defer_store_to_concierge", return_value=False)
def test_classify_inquiry_respects_router_dispatch_store(_defer):
    from src.services.store_inquiry_handler import classify_inquiry_with_llm

    triage = {
        "category": "Other",
        "subcategory": "store_inquiry",
        "_intent_router_dispatch": True,
        "confidence": 0.9,
    }
    result = classify_inquiry_with_llm("トイレはどこですか", MagicMock(), triage)
    assert result["is_store_inquiry"] is True
