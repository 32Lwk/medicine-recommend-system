"""SessionOps Web status/summarize テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.session_ops import try_handle_session_ops


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_web_status(_db, _is_line):
    session: dict = {"messages": []}
    resp = try_handle_session_ops(
        session,
        "web-session-1",
        "ステータスを教えて",
        MagicMock(),
    )
    assert resp is not None
    assert session["messages"][-1]["session_agent_kind"] == "status"
    assert session.get("dialogue_state", {}).get("version") == 1


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
def test_web_delete_not_handled(_is_line):
    session: dict = {"messages": []}
    resp = try_handle_session_ops(
        session,
        "web-session-1",
        "履歴消して",
        MagicMock(),
    )
    assert resp is None


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:U1")
@patch("src.agents.session_agent.try_handle_session_request")
def test_line_pending_syncs_dialogue_state(mock_handle, _owner, _is_line, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")

    def _set_pending(session, sid, text, client, **kwargs):
        session["pending_memory_delete"] = {"scope": "all", "owner": sid}
        return ({"status": "ok", "message_count": 1}, 200)

    mock_handle.side_effect = _set_pending
    session: dict = {"messages": []}
    resp = try_handle_session_ops(session, "line:U1", "履歴消して", MagicMock())
    assert resp is not None
    assert session["dialogue_state"]["pending"]["session_delete"]["scope"] == "all"
