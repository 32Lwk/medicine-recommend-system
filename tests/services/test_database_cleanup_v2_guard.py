"""cleanup_expired_sessions の v2 テストセッション除外 SQL。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.database import DatabaseManager


@patch.object(DatabaseManager, "get_connection")
@patch.object(DatabaseManager, "put_connection")
def test_cleanup_expired_sessions_escapes_percent_in_v2_guard(mock_put, mock_get) -> None:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 0
    conn.cursor.return_value = cursor
    mock_get.return_value = conn

    db = DatabaseManager()
    db.cleanup_expired_sessions(3600)

    executed_sql = cursor.execute.call_args[0][0]
    assert "%%local-v2-chat-test%%" in executed_sql
    assert "v2-test-%%" in executed_sql
    assert "%local-v2-chat-test%" not in executed_sql.replace("%%", "")


@patch.object(DatabaseManager, "get_connection")
@patch.object(DatabaseManager, "put_connection")
def test_cleanup_expired_sessions_exclude_list_uses_placeholders(mock_put, mock_get) -> None:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 1
    conn.cursor.return_value = cursor
    mock_get.return_value = conn

    db = DatabaseManager()
    db.cleanup_expired_sessions(3600, exclude_session_ids=["sess-a", "sess-b"])

    sql, params = cursor.execute.call_args[0]
    assert "NOT IN" in sql
    assert params == ("sess-a", "sess-b")
    assert "%%local-v2-chat-test%%" in sql
