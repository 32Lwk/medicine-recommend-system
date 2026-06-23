"""不適切メッセージルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_inappropriate_route import (
    detect_inappropriate_message,
    handle_inappropriate_message_if_detected,
)
from src.security.aggressive_input import AGGRESSIVE_INPUT_NOTICE_MESSAGE


def test_detect_numeric_slang_absolute_block_not_inappropriate_route():
    from src.security.aggressive_input import is_aggressive_expression, is_non_absolute_aggressive_expression

    assert is_aggressive_expression("69")[0]
    assert not is_non_absolute_aggressive_expression("69")[0]
    assert not detect_inappropriate_message("69")


@patch("src.handlers.chat.chat_inappropriate_route.save_session_to_db")
def test_handle_returns_aggressive_notice(mock_save):
    session = {"messages": []}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"
    with patch(
        "src.security.aggressive_input.is_non_absolute_aggressive_expression",
        return_value=(True, "69"),
    ):
        resp = handle_inappropriate_message_if_detected(
            session, client, "sid", "msg", "69", MagicMock()
        )
    assert resp is not None
    assert resp[0]["status"] == "ok"
    assert resp[0]["response"] == AGGRESSIVE_INPUT_NOTICE_MESSAGE
    assert session["messages"][1]["diagnosis"]["kind"] == "aggressive_input"
