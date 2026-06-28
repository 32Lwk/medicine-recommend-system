"""RoutingContext のユニットテスト"""
from unittest.mock import MagicMock, patch

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


@patch("config.llm_flags.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.history.resolve_conversation_history_with_fallback")
def test_resolve_history_for_routing_v2(mock_resolve, _v2):
    from src.services.routing_context import _resolve_history_for_routing

    mock_resolve.return_value = [{"type": "user", "content": "routing v2"}]
    msgs = _resolve_history_for_routing({}, "line:U1")
    assert msgs == [{"type": "user", "content": "routing v2"}]
    mock_resolve.assert_called_once_with({}, "line:U1", agent_kind="default")
