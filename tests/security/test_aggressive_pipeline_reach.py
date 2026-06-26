"""攻撃的入力がパイプライン上で aggressive_input 応答に到達することを保証する。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_input_validator import validate_and_block_input
from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response
from src.security.aggressive_input import AGGRESSIVE_INPUT_NOTICE_MESSAGE


def _bot_kind(session: dict) -> str:
    bot = session["messages"][-1]
    diagnosis = bot.get("diagnosis") or {}
    return str(diagnosis.get("kind") or "")


@patch("src.handlers.chat.chat_input_validator._persist_block_messages_to_db")
def test_shine_reaches_aggressive_input_via_validator(_mock_persist):
    session: dict = {"messages": [], "username": "tester"}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    sanitized, err = validate_and_block_input(session, client, "しね", "line:U1")

    assert sanitized is None
    assert err is not None
    assert err[0]["response"] == AGGRESSIVE_INPUT_NOTICE_MESSAGE
    assert _bot_kind(session) == "aggressive_input"
    assert session["messages"][-1]["diagnosis"]["title"] == "入力について"


@patch("src.handlers.chat.chat_inappropriate_route.save_session_to_db")
def test_kill_threat_reaches_aggressive_input_via_inappropriate_route(mock_save):
    from src.handlers.chat.chat_inappropriate_route import handle_inappropriate_message_if_detected

    session: dict = {"messages": []}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = handle_inappropriate_message_if_detected(
        session, client, "line:U1", "殺すぞ", "殺すぞ", MagicMock()
    )

    assert resp is not None
    assert _bot_kind(session) == "aggressive_input"
    assert resp[0]["response"] == AGGRESSIVE_INPUT_NOTICE_MESSAGE
    mock_save.assert_called()


@patch("src.services.counseling.counseling_logger.log_counseling_response")
@patch("src.handlers.chat.chat_input_validator._persist_block_messages_to_db")
def test_finalize_pipeline_logs_aggressive_input(_mock_persist, mock_log):
    session: dict = {"messages": [], "username": "tester"}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    _, err = validate_and_block_input(session, client, "しね", "line:U1")
    assert err is not None

    finalize_pipeline_response(
        session,
        "line:U1",
        client,
        0,
        err,
        user_message="しね",
    )
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["user_input"] == "しね"
    assert mock_log.call_args.kwargs["response_type"] == "aggressive_input"
