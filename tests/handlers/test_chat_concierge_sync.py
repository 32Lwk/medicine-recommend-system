"""get_next_user_number / concierge sync のテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.chat_concierge_route import _resolve_sync_username
from src.services import session_manager as sm


def test_get_next_user_number_skips_none_username():
    sm._all_sessions.clear()
    with patch.object(sm, "get_all_sessions_from_db", return_value={"s1": {"username": None}}):
        assert sm.get_next_user_number() == 1


def test_resolve_sync_username_uses_line_profile():
    session = {}
    existing = {
        "username": None,
        "line_profile": {"displayName": "宥翔"},
    }
    with patch("src.handlers.chat.chat_concierge_route.get_next_user_number") as mock_num:
        name = _resolve_sync_username(session, "line:U1", existing)
    assert name == "宥翔"
    mock_num.assert_not_called()
