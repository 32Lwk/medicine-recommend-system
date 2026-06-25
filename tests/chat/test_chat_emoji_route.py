"""LINE 絵文字 pre-triage ルートのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_emoji_route import try_emoji_pre_triage_route
from src.utils.chat_http_context import ChatClientInfo


def _client():
    return ChatClientInfo(client_ip="line-webhook", user_agent="test")


@patch("src.handlers.chat.chat_emoji_route.build_emoji_soft_intro_text", return_value="INTRO")
@patch("src.services.counseling.counseling_logger.log_counseling_response")
def test_offensive_emoji_soft_intro_line_only(mock_log, mock_intro):
    session = {"messages": []}
    resp = try_emoji_pre_triage_route(
        session,
        _client(),
        "line:Utest",
        "🖕",
        "🖕",
        MagicMock(),
    )
    assert resp is not None
    assert resp[0]["status"] == "ok"
    bot = session["messages"][-1]
    assert bot.get("diagnosis", {}).get("message") == "INTRO" or bot.get("content") == "INTRO"
    mock_intro.assert_called_once()
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["response_type"] == "emoji_soft_intro"
    assert mock_log.call_args.kwargs["user_input"] == "🖕"


def test_non_line_session_skipped():
    session = {"messages": []}
    resp = try_emoji_pre_triage_route(
        session,
        _client(),
        "web-session",
        "🖕",
        "🖕",
        MagicMock(),
    )
    assert resp is None


@patch("src.handlers.chat.chat_emoji_route.classify_emoji_intent_llm", return_value=("unknown", 0.5))
@patch("src.handlers.chat.chat_emoji_route.build_emoji_unknown_ack_text", return_value="ACK")
@patch("src.services.counseling.counseling_logger.log_counseling_response")
def test_emoji_only_unknown_ack(mock_log, mock_ack, mock_llm):
    session = {"messages": []}
    resp = try_emoji_pre_triage_route(
        session,
        _client(),
        "line:Utest",
        "🤔",
        "🤔",
        MagicMock(),
    )
    assert resp is not None
    mock_llm.assert_called_once()
    bot = session["messages"][-1]
    assert bot.get("diagnosis", {}).get("message") == "ACK" or bot.get("content") == "ACK"
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["response_type"] == "emoji_unknown_ack"


@patch("src.handlers.chat.chat_emoji_route.classify_emoji_intent_llm")
def test_text_with_emoji_skips_llm_unless_offensive(mock_llm):
    session = {"messages": []}
    resp = try_emoji_pre_triage_route(
        session,
        _client(),
        "line:Utest",
        "痛い😭",
        "痛い😭",
        MagicMock(),
    )
    assert resp is None
    mock_llm.assert_not_called()


@patch("src.handlers.chat.chat_concierge_route.try_concierge_response")
@patch("src.handlers.chat.chat_emoji_route.classify_emoji_intent_llm", return_value=("greeting", 0.9))
def test_emoji_only_greeting_routes_concierge(mock_llm, mock_concierge):
    mock_concierge.return_value = ({"status": "ok", "message_count": 2}, 200)
    session = {"messages": []}
    resp = try_emoji_pre_triage_route(
        session,
        _client(),
        "line:Utest",
        "👋",
        "👋",
        MagicMock(),
    )
    assert resp is not None
    triage = mock_concierge.call_args.kwargs.get("triage_result") or mock_concierge.call_args[0][5]
    assert triage["concierge_intent"] == "greeting"
    assert triage["concierge_intent_source"] == "emoji_llm"
