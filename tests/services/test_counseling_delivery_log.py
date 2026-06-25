"""counseling_detail 配信フォールバックログのテスト。"""

from __future__ import annotations

from unittest.mock import patch

from src.services.counseling.counseling_logger import (
    maybe_log_line_turn_counseling_detail,
    mark_counseling_detail_logged,
    was_counseling_detail_logged,
)


def test_was_counseling_detail_logged() -> None:
    session: dict = {}
    assert was_counseling_detail_logged(session, "hello") is False
    mark_counseling_detail_logged(session, "hello")
    assert was_counseling_detail_logged(session, "hello") is True
    assert was_counseling_detail_logged(session, "other") is False


@patch("src.services.counseling.counseling_logger.log_counseling_response")
@patch(
    "src.services.counseling.counseling_logger.resolve_bot_message_plain_text",
    return_value="bot reply text",
)
def test_maybe_log_line_turn_logs_when_not_marked(mock_plain, mock_log) -> None:
    session: dict = {"messages": []}
    bot = {"content": "bot reply text", "kind": "emoji_unknown_ack"}
    maybe_log_line_turn_counseling_detail(session, "line:U1", "😄", bot)
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["response_type"] == "emoji_unknown_ack"
    assert mock_log.call_args.kwargs["session"] is session


@patch("src.services.counseling.counseling_logger.log_counseling_response")
@patch(
    "src.services.counseling.counseling_logger.resolve_bot_message_plain_text",
    return_value="bot reply text",
)
def test_maybe_log_line_turn_skips_when_already_marked(mock_plain, mock_log) -> None:
    session: dict = {"messages": []}
    mark_counseling_detail_logged(session, "😄")
    bot = {"content": "bot reply text", "kind": "emoji_unknown_ack"}
    maybe_log_line_turn_counseling_detail(session, "line:U1", "😄", bot)
    mock_log.assert_not_called()
