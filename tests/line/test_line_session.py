"""LINE セッション紐付けのユニットテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.line.line_session import (
    count_bot_messages_in_session,
    get_latest_bot_message_from_session,
    resolve_latest_bot_message,
)


def test_count_bot_messages_handles_none_messages():
    assert count_bot_messages_in_session({"messages": None}) == 0
    assert get_latest_bot_message_from_session({"messages": None}) is None


def test_get_latest_bot_message_from_session():
    session = {
        "messages": [
            {"type": "user", "content": "頭が痛い"},
            {"type": "bot", "content": "古い"},
            {"type": "bot", "content": "最新", "diagnosis": {"status": "success"}},
        ]
    }
    bot = get_latest_bot_message_from_session(session)
    assert bot is not None
    assert bot["content"] == "最新"


def test_resolve_latest_bot_message_prefers_in_memory():
    session = {"messages": [{"type": "bot", "content": "memory"}]}
    with patch(
        "src.handlers.line.line_session.get_latest_bot_message",
        return_value={"type": "bot", "content": "db"},
    ) as mock_db:
        bot = resolve_latest_bot_message(session, "line:Utest")
    assert bot["content"] == "memory"
    mock_db.assert_not_called()


def test_resolve_latest_bot_message_falls_back_to_db():
    session = MagicMock()
    session.get.return_value = []
    db_bot = {"type": "bot", "content": "db"}
    with patch(
        "src.handlers.line.line_session.get_latest_bot_message",
        return_value=db_bot,
    ):
        bot = resolve_latest_bot_message(session, "line:Utest")
    assert bot == db_bot
