"""persist_session_attributes_only の LINE throttle テスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services import session_manager as sm


def test_persist_session_attributes_only_throttles_line():
    data = {"user_attributes": {"gender": "女性"}, "last_activity": "now"}
    with (
        patch("src.handlers.line.line_session.is_line_session_id", return_value=True),
        patch.object(sm, "maybe_persist_session_activity") as mock_maybe,
        patch.object(sm, "save_session_to_db") as mock_save,
    ):
        sm.persist_session_attributes_only("line:U1", data)
        sm.persist_session_attributes_only("line:U1", data)

    assert mock_maybe.call_count == 2
    mock_save.assert_not_called()


def test_persist_session_attributes_only_saves_web_immediately():
    data = {"user_attributes": {"age": 30}}
    with (
        patch("src.handlers.line.line_session.is_line_session_id", return_value=False),
        patch.object(sm, "maybe_persist_session_activity") as mock_maybe,
        patch.object(sm, "save_session_to_db") as mock_save,
    ):
        sm.persist_session_attributes_only("web:abc", data)

    mock_save.assert_called_once()
    mock_maybe.assert_not_called()


def test_get_session_from_db_line_skips_db_read():
    sm._all_sessions["line:U1"] = {"session_id": "line:U1", "messages": [{"type": "user"}]}
    mock_db = patch.object(sm, "get_database")
    with mock_db as get_db:
        result = sm.get_session_from_db("line:U1")
    get_db.assert_not_called()
    assert result["messages"][0]["type"] == "user"


def test_get_line_session_admin_snapshot_merges_db_archive_with_mem_live():
    sm._all_sessions["line:U1"] = {
        "session_id": "line:U1",
        "messages": [{"type": "user", "content": "new", "timestamp": "2026-06-22T07:00:00"}],
    }
    db_archive = {
        "session_id": "line:U1",
        "message_archive": [
            {"type": "user", "content": "old", "timestamp": "2026-06-21T09:00:00"},
        ],
        "messages": [],
    }
    mock_db = patch.object(sm, "get_database")
    with (
        mock_db as get_db,
        patch.object(sm, "_db_usable", return_value=True),
        patch("src.handlers.line.line_session.is_line_session_id", return_value=True),
        patch("src.handlers.line.line_session.normalize_line_session_id", side_effect=lambda s: s),
    ):
        get_db.return_value.get_session.return_value = db_archive
        result = sm.get_line_session_admin_snapshot("line:U1")
    get_db.return_value.get_session.assert_called_once_with("line:U1")
    assert result is not None
    contents = [m.get("content") for m in result.get("message_archive") or []]
    assert "old" in contents
    assert "new" in contents


def test_get_next_user_number_skips_none_username():
    with patch.object(sm, "get_all_sessions_from_db", return_value={"s1": {"username": None}}):
        assert sm.get_next_user_number() == 1
