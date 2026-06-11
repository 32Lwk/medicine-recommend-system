"""不適切メッセージルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_inappropriate_route import (
    detect_inappropriate_message,
    handle_inappropriate_message_if_detected,
)


def test_detect_numeric_slang():
    assert detect_inappropriate_message("69")


@patch("src.services.counseling_response.start_counseling_mode")
@patch("src.services.counseling_response.generate_follow_up_questions", return_value=[])
@patch("src.services.counseling_response.generate_counseling_response", return_value="応答")
@patch("src.services.counseling_response.log_counseling_response")
def test_handle_returns_response(mock_log, mock_gen, mock_q, mock_start):
    session = {"messages": []}
    with patch(
        "src.handlers.chat.chat_inappropriate_route.detect_inappropriate_message",
        return_value=True,
    ):
        resp = handle_inappropriate_message_if_detected(
            session, MagicMock(), "sid", "msg", "69", MagicMock()
        )
    assert resp is not None
    assert resp[0]["status"] == "ok"
