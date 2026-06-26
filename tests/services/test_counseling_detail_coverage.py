"""counseling_detail が全 bot 応答経路で記録されることのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response
from src.services.counseling.counseling_logger import maybe_log_turn_counseling_detail


@patch("src.services.counseling.counseling_logger.log_counseling_response")
def test_maybe_log_session_agent_status(mock_log):
    session = {
        "messages": [
            {"type": "user", "content": "ステータスを教えて"},
            {
                "type": "bot",
                "content": "sage_status",
                "session_agent_kind": "status",
                "diagnosis": {
                    "kind": "session_status",
                    "message": "セッション統合ステータス",
                    "title": "ステータス",
                },
            },
        ]
    }
    bot = session["messages"][-1]
    maybe_log_turn_counseling_detail(session, "line:U1", "ステータスを教えて", bot)
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["response_type"] == "status"
    assert mock_log.call_args.kwargs["user_input"] == "ステータスを教えて"


@patch("src.services.counseling.counseling_logger.log_counseling_response")
@patch("src.handlers.chat.chat_input_validator._persist_block_messages_to_db")
def test_finalize_pipeline_logs_without_explicit_sid(_mock_persist, mock_log):
    from src.handlers.chat.chat_input_validator import validate_and_block_input

    session = {"messages": [], "username": "web-user", "session_id": "web-sid-1"}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    _, err = validate_and_block_input(session, client, "しね", None)
    assert err is not None

    finalize_pipeline_response(session, None, client, 0, err, user_message="しね")
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["session_id"] == "web-sid-1"
