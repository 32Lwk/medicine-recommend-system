"""persist_line_session がフルセッションを永続化することのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.line.line_session import persist_line_session


def test_persist_line_session_writes_messages_and_attributes():
    session = MagicMock()
    session.get = MagicMock(
        side_effect=lambda key, default=None: {
            "messages": [{"type": "user", "content": "頭痛"}],
            "user_attributes": {"age": 30},
        }.get(key, default)
    )

    with patch(
        "src.handlers.line.line_session.persist_session_from_chat_state"
    ) as mock_persist:
        persist_line_session("line:U1", session)

    mock_persist.assert_called_once_with("line:U1", session, request=None)
