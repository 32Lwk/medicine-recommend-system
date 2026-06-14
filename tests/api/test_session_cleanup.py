"""セッションクリーンアップ・purge のユニットテスト。"""
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.services.session_manager import (
    get_cleanup_exclude_session_ids,
    purge_empty_sessions_on_startup,
)


def test_get_cleanup_exclude_session_ids_includes_queue_and_crisis():
    with patch("src.services.session_manager.get_manual_reply_queue", return_value=[
        {"session_id": "q1"},
    ]):
        with patch("src.services.session_manager.get_all_sessions_from_db", return_value={
            "c1": {"crisis_detected": True, "messages": []},
            "ok1": {"messages": [{"type": "user", "content": "hi"}]},
        }):
            exclude = get_cleanup_exclude_session_ids()
    assert "q1" in exclude
    assert "c1" in exclude


def test_purge_empty_sessions_on_startup_calls_db():
    mock_db = MagicMock()
    mock_db.connection = True
    mock_db.connection_pool = True
    mock_db.purge_all_empty_sessions.return_value = 3
    with patch("src.services.session_manager.get_database", return_value=mock_db):
        with patch(
            "src.services.session_manager.get_cleanup_exclude_session_ids",
            return_value=["q1"],
        ):
            count = purge_empty_sessions_on_startup()
    assert count == 3
    mock_db.purge_all_empty_sessions.assert_called_once_with(exclude_session_ids=["q1"])


def test_cleanup_old_sessions_skip_empty_sessions():
    from src.services.session_manager import cleanup_old_sessions

    mock_db = MagicMock()
    mock_db.connection = True
    mock_db.connection_pool = True
    mock_db.cleanup_expired_sessions.return_value = 0
    old_ts = time.time() - 99999
    with patch("src.services.session_manager.get_database", return_value=mock_db), patch(
        "src.services.session_manager.get_all_sessions_from_db",
        return_value={"e1": {"messages": [], "last_activity": old_ts}},
    ), patch(
        "src.services.session_manager.get_cleanup_exclude_session_ids", return_value=[]
    ), patch("src.services.session_manager._last_cleanup_time", 0):
        cleanup_old_sessions(force=True, skip_empty_sessions=True)
    mock_db.cleanup_expired_sessions.assert_called_once()
    assert mock_db.cleanup_expired_sessions.call_args.kwargs["skip_empty_sessions"] is True


def test_line_session_sql_guard_avoids_percent_wildcard():
    from src.services.database import DatabaseManager

    guard = DatabaseManager._line_session_sql_guard(object())
    assert "%" not in guard
    assert "line:" in guard
