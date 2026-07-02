"""Phase 4b-5a: LEGACY_FALLBACK_TRIM フラグと legacy 経路ガード。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_post_pipeline import (
    ChatPostContext,
    _legacy_trim_blocks_path,
)


def _ctx(*, session_extra: dict | None = None, triage_extra: dict | None = None):
    session = {"messages": [], "user_attributes": {}}
    if session_extra:
        session.update(session_extra)
    triage = {"category": "Other", "confidence": 0.9, "subcategory": "general_other"}
    if triage_extra:
        triage.update(triage_extra)
    return ChatPostContext(
        session=session,
        client_info=MagicMock(),
        sid="web:trim-test",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="test",
        sanitized_message="test",
        processed_message="test",
        triage_result=triage,
        trace_id="trace-trim",
        recommendation_client=MagicMock(),
    )


@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=False)
def test_trim_off_never_blocks(_trim):
    ctx = _ctx(session_extra={"_router_dispatch_handled_turn": True})
    assert _legacy_trim_blocks_path(ctx, "route_triage_category") is False


@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=True)
def test_trim_on_dispatch_handled_blocks_category(_trim):
    ctx = _ctx(session_extra={"_router_dispatch_handled_turn": True})
    assert _legacy_trim_blocks_path(ctx, "route_triage_category") is True


@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=True)
def test_trim_on_handler_none_allows_orchestrator(_trim):
    ctx = _ctx(
        session_extra={
            "_router_dispatch_attempted": True,
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "architecture",
            },
        }
    )
    assert _legacy_trim_blocks_path(ctx, "orchestrator") is False


@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=True)
def test_trim_on_unknown_allows_fallback(_trim):
    ctx = _ctx(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Unknown",
                "sub_route": None,
            }
        }
    )
    assert _legacy_trim_blocks_path(ctx, "orchestrator") is False


@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=True)
def test_trim_on_clarification_allows_fallback(_trim):
    ctx = _ctx(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "clarification",
            }
        }
    )
    assert _legacy_trim_blocks_path(ctx, "other_post_orchestrator") is False


@patch("config.llm_flags.is_intent_router_dispatch_enabled", return_value=True)
@patch("config.llm_flags.is_legacy_fallback_trim_enabled", return_value=True)
@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
@patch("src.handlers.chat.chat_category_route.route_triage_category")
@patch("src.handlers.chat_orchestrator.try_orchestrator_route", return_value=None)
@patch("src.handlers.chat.chat_post_pipeline._run_other_post_orchestrator_followups", return_value=None)
@patch("src.handlers.chat.llm_pipeline_guard.try_llm_pipeline_short_circuit", return_value=None)
@patch("src.handlers.chat.chat_confidence_route.check_triage_confidence", return_value=None)
@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_pipeline_skips_category_route_when_dispatch_handled(
    _agent,
    _conf,
    _short,
    _other,
    mock_orch,
    mock_cat,
    _primary,
    _trim,
    _dispatch,
):
    from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

    session = {
        "messages": [],
        "user_attributes": {},
        "_router_dispatch_handled_turn": True,
        "last_triage_result": {"category": "Physical", "confidence": 0.95},
    }
    client = MagicMock()
    client.user_agent = "test"
    client.client_ip = "127.0.0.1"

    with patch("src.handlers.chat.chat_post_pipeline.parse_incoming_message", return_value="頭痛"):
        with patch("src.handlers.chat.chat_post_init.empty_message_response", return_value=None):
            with patch("src.handlers.chat.chat_triage.run_triage", return_value=(None, session["last_triage_result"])):
                with patch("src.handlers.chat.chat_post_pipeline._try_session_ops_handler", return_value=None):
                    with patch("src.handlers.chat.chat_emoji_route.try_emoji_pre_triage_route", return_value=None):
                        with patch("src.handlers.chat.chat_post_pipeline._run_moderation_if_needed"):
                            with patch("src.handlers.chat.chat_counseling_flow.run_counseling_flow", return_value=(None, session["last_triage_result"])):
                                with patch("src.handlers.chat.chat_triage_follow_ups.run_triage_follow_ups", return_value=(None, False)):
                                    with patch("src.handlers.chat.chat_preprocess_route.preprocess_user_message", return_value=("頭痛", "頭痛")):
                                        with patch("src.handlers.chat.chat_post_pipeline.sync_routing_context"):
                                            with patch("src.dialogue.routing.shadow.run_and_record_shadow"):
                                                with patch("src.handlers.chat.chat_question_route.handle_question_flow") as mock_q:
                                                    mock_q.return_value = MagicMock(response=None, is_question=False, user_message="頭痛", sanitized_message="頭痛")
                                                    with patch("src.handlers.chat.chat_session_route.handle_chat_end_if_requested", return_value=None):
                                                        with patch("src.handlers.chat.chat_session_route.append_user_message_if_needed"):
                                                            with patch("src.handlers.chat.chat_session_route.sync_messages_to_db_for_admin"):
                                                                with patch("src.handlers.chat.chat_symptom_route.run_symptom_recommendation", return_value=({"status": "ok"}, 200)):
                                                                    with patch("src.utils.input_helpers.should_fallback_to_symptom_recommendation", return_value=True):
                                                                        with patch("src.handlers.chat.emergency_dispatch.is_otc_flow_blocked", return_value=False):
                                                                            run_chat_post_pipeline(session, client, "頭痛", "web:trim-test", MagicMock())

    mock_cat.assert_not_called()
    mock_orch.assert_not_called()
