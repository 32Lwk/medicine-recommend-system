"""RoutingContext のユニットテスト"""
from unittest.mock import MagicMock

from src.services.routing_context import RoutingContext


def test_build_includes_triage_and_history_digest():
    session = MagicMock()
    session.get.side_effect = lambda k, d=None: {
        "last_triage_result": {"category": "Ask", "confidence": 0.9},
        "messages": [{"type": "user", "content": "頭痛"}],
    }.get(k, d)
    ctx = RoutingContext.build(
        session,
        "sid-1",
        "風邪薬は？",
        "風邪薬は？",
        {"category": "Ask", "confidence": 0.95},
        pending_route_is_question=True,
    )
    assert ctx.triage_category == "Ask"
    assert ctx.triage_confidence == 0.95
    assert ctx.pending_route_is_question is True
    assert ctx.history_digest
    assert len(ctx.history_messages) == 1


def test_triage_category_defaults_empty():
    ctx = RoutingContext(
        session_id=None,
        user_text="",
        sanitized_text="",
    )
    assert ctx.triage_category == ""
    assert ctx.triage_confidence == 1.0
    assert ctx.store_gate_evaluated is False
    assert ctx.store_probable is None
