"""persist_session_from_chat_state の sid 整合性テスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.session_manager import persist_session_from_chat_state


def test_persist_skips_on_session_sid_mismatch():
    session = {"_id": "wrong", "messages": [{"type": "user", "content": "hi"}]}
    with patch("src.services.session_manager.ensure_session_persisted") as persist:
        persist_session_from_chat_state("correct", session)
        persist.assert_not_called()


def test_persist_proceeds_when_sid_matches():
    session = {"_id": "abc", "messages": [{"type": "user", "content": "hi"}]}
    with patch("src.services.session_manager.get_session_from_db", return_value={}):
        with patch("src.services.session_manager.ensure_session_persisted") as persist:
            persist_session_from_chat_state("abc", session)
            persist.assert_called_once()
