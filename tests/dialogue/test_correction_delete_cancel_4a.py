"""p3-correction-sessionops 4a: 削除確認キャンセルの明示応答（UX_CORRECTION_DELETE_CANCEL）。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.dialogue.session_ops import (
    is_awaiting_memory_delete_confirmation,
    try_answer_pending_delete_cancel,
    try_handle_pending_delete_cancel,
    try_handle_session_ops,
)


def _confirm_bot() -> dict:
    return {
        "type": "bot",
        "content": "sage_status",
        "diagnosis": {"kind": "memory_delete_confirm", "message": "削除確認"},
    }


@pytest.mark.parametrize("cancel_text", ["キャンセル", "やっぱり消さない"])
def test_flag_off_does_not_restore_pending_from_dialogue_state(cancel_text, monkeypatch):
    monkeypatch.delenv("UX_CORRECTION_DELETE_CANCEL", raising=False)
    session = {
        "messages": [{"type": "user", "content": "履歴消して"}, _confirm_bot()],
        "dialogue_state": {
            "version": 1,
            "pending": {"session_delete": {"scope": "all"}},
            "concierge": {},
            "counseling": {},
            "handoff": {},
            "flags": {},
        },
    }
    assert try_handle_pending_delete_cancel(session, "web:t", cancel_text) is False
    assert "pending_memory_delete" not in session


@pytest.mark.parametrize("cancel_text", ["キャンセル", "やっぱり消さない"])
def test_flag_on_restores_pending_from_dialogue_state(cancel_text, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("UX_CORRECTION_DELETE_CANCEL", "true")
    session = {
        "messages": [{"type": "user", "content": "履歴消して"}, _confirm_bot()],
        "dialogue_state": {
            "version": 1,
            "pending": {"session_delete": {"scope": "all"}},
            "concierge": {},
            "counseling": {},
            "handoff": {},
            "flags": {},
        },
    }
    client = MagicMock()
    resp = try_handle_session_ops(session, "web:t", cancel_text, client)
    assert resp is not None
    assert "pending_memory_delete" not in session
    msgs = session.get("messages") or []
    last_bot = next(m for m in reversed(msgs) if m.get("type") == "bot")
    assert last_bot.get("diagnosis", {}).get("kind") == "memory_delete_cancelled"


def test_flag_on_restores_from_last_bot_confirm_only(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("UX_CORRECTION_DELETE_CANCEL", "true")
    session = {
        "messages": [{"type": "user", "content": "記憶を消して"}, _confirm_bot()],
    }
    assert is_awaiting_memory_delete_confirmation(session, allow_bot_confirm_fallback=True)
    client = MagicMock()
    resp = try_handle_session_ops(session, "web:t", "キャンセル", client)
    assert resp is not None
    last_bot = session["messages"][-1]
    assert last_bot.get("diagnosis", {}).get("kind") == "memory_delete_cancelled"


def test_two_turn_setup_cancel_with_pending_legacy(monkeypatch):
    """pending_memory_delete が残っている通常経路（フラグ不要）。"""
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.delenv("UX_CORRECTION_DELETE_CANCEL", raising=False)
    client = MagicMock()
    session: dict = {"messages": []}
    assert try_handle_session_ops(session, "web:t", "履歴消して", client) is not None
    assert session.get("pending_memory_delete")
    resp = try_handle_session_ops(session, "web:t", "やっぱり消さない", client)
    assert resp is not None
    assert "pending_memory_delete" not in session
    assert session["messages"][-1]["diagnosis"]["kind"] == "memory_delete_cancelled"


def test_counseling_bypass_returns_cancelled(monkeypatch):
    monkeypatch.setenv("UX_CORRECTION_DELETE_CANCEL", "true")
    session = {
        "messages": [{"type": "user", "content": "記憶を消して"}, _confirm_bot()],
    }
    resp = try_answer_pending_delete_cancel(session, "web:t", "キャンセル")
    assert resp is not None
    assert session["messages"][-1]["diagnosis"]["kind"] == "memory_delete_cancelled"
