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

    mock_persist.assert_called_once_with(
        "line:U1", session, request=None, force_persist=True
    )


def test_persist_session_from_chat_state_line_throttle_when_not_forced():
    from src.services import session_manager as sm

    session = {"messages": [{"type": "user", "content": "a"}], "user_attributes": {}}
    with (
        patch.object(sm, "get_session_from_db", return_value={}),
        patch.object(sm, "maybe_persist_session_activity") as mock_maybe,
        patch.object(sm, "ensure_session_persisted") as mock_ensure,
    ):
        sm.persist_session_from_chat_state("line:U1", session, force_persist=False)

    mock_maybe.assert_called_once()
    mock_ensure.assert_not_called()


def test_persist_session_from_chat_state_line_force_at_turn_end():
    from src.services import session_manager as sm

    session = {"messages": [{"type": "user", "content": "a"}], "user_attributes": {}}
    with (
        patch.object(sm, "get_session_from_db", return_value={}),
        patch.object(sm, "maybe_persist_session_activity") as mock_maybe,
        patch.object(sm, "ensure_session_persisted") as mock_ensure,
    ):
        sm.persist_session_from_chat_state("line:U1", session, force_persist=True)

    mock_ensure.assert_called_once()
    mock_maybe.assert_not_called()


def test_persist_line_session_no_block_when_db_unavailable():
    """DB 不可時もターン終了 persist が再接続ループでブロックしない。"""
    import time

    from src.services import session_manager as sm

    mock_db = MagicMock()
    mock_db.is_available.return_value = False
    mock_db.connection = None
    mock_db.connection_pool = None
    mock_db.startup_skip_reason = "connect_failed"

    session = {
        "messages": [{"type": "user", "content": "こんにちは"}],
        "user_attributes": {},
    }

    with patch.object(sm, "get_database", return_value=mock_db):
        sm._db_persist_enabled = False
        start = time.monotonic()
        sm.persist_session_from_chat_state("line:U1", session, force_persist=True)
        elapsed = time.monotonic() - start

    assert elapsed < 0.5
    assert sm.get_session_from_memory("line:U1") is not None
