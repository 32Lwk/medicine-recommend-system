"""LINE セッション trim / クリアのテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.chat_session_route import handle_chat_end_if_requested
from src.handlers.line.line_session import (
    LINE_SESSION_MAX_MESSAGES,
    clear_line_session_state,
    trim_line_session_messages,
)


def test_trim_line_session_messages_keeps_tail():
    session = {"messages": [{"type": "user", "content": f"m{i}"} for i in range(30)]}
    trim_line_session_messages(session)
    assert len(session["messages"]) == LINE_SESSION_MAX_MESSAGES
    assert session["messages"][0]["content"] == f"m{30 - LINE_SESSION_MAX_MESSAGES}"


def test_clear_line_session_state_resets_messages():
    session = {
        "messages": [{"type": "user", "content": "a"}],
        "counseling_mode": {"active": True},
        "concierge_state": {"off_topic_turns": 3},
    }
    clear_line_session_state(session)
    assert session["messages"] == []
    assert "counseling_mode" not in session
    assert session["concierge_state"]["off_topic_turns"] == 0


@patch("src.handlers.chat.chat_session_route.save_session_to_db")
@patch("src.handlers.chat.chat_session_route.get_session_from_db", return_value={"messages": [{"type": "user"}]})
def test_line_chat_end_clears_history(mock_get, mock_save):
    session = {"messages": [{"type": "user", "content": "頭痛"}], "username": "LINEユーザー"}
    resp = handle_chat_end_if_requested(session, "line:Uabc", "終了")
    assert resp is not None
    assert len(session["messages"]) == 1
    assert session["messages"][0].get("chat_ended")
    saved = mock_save.call_args[0][1]
    assert saved["session_active"] is False
    assert "line_feedback_pending" not in saved
