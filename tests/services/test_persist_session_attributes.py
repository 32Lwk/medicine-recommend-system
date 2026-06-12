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
