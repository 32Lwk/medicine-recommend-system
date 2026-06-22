"""session_manager の DB フォールバック・ポーリング間引きのテスト"""
import logging
from unittest.mock import MagicMock, patch

import pytest

from src.services import session_manager as sm


@pytest.fixture(autouse=True)
def reset_session_manager_state():
    sm._all_sessions.clear()
    sm._db_persist_enabled = None
    sm._memory_fallback_logged = False
    sm._last_db_persist_at.clear()
    sm._ai_auto_reply = True
    sm._ai_auto_reply_pending = False
    sm._admin_mode = False
    sm._admin_mode_pending = False
    yield
    sm._all_sessions.clear()
    sm._db_persist_enabled = None
    sm._memory_fallback_logged = False
    sm._last_db_persist_at.clear()
    sm._ai_auto_reply = True
    sm._ai_auto_reply_pending = False
    sm._admin_mode = False
    sm._admin_mode_pending = False


def test_save_session_to_db_logs_memory_fallback_once(caplog):
    mock_db = MagicMock()
    mock_db.is_available.return_value = False
    mock_db.startup_skip_reason = 'no_url'

    with patch.object(sm, 'get_database', return_value=mock_db):
        with caplog.at_level(logging.INFO):
            sm.save_session_to_db('sid-1', {'session_id': 'sid-1', 'messages': []})
            sm.save_session_to_db('sid-2', {'session_id': 'sid-2', 'messages': []})

    assert sm._memory_fallback_logged
    assert sum(1 for r in caplog.records if 'メモリに保存' in r.message) == 1
    assert 'sid-1' in sm._all_sessions
    assert 'sid-2' in sm._all_sessions


def test_maybe_persist_skips_db_when_unavailable():
    mock_db = MagicMock()
    mock_db.is_available.return_value = False
    data = {'session_id': 'sid-a', 'messages': []}

    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = False
        sm.maybe_persist_session_activity('sid-a', data)
        sm.maybe_persist_session_activity('sid-a', data)

    mock_db.save_session.assert_not_called()
    assert sm._all_sessions['sid-a'] is data


def test_maybe_persist_throttles_db_writes():
    mock_db = MagicMock()
    mock_db.is_available.return_value = True
    mock_db.save_session.return_value = True
    data = {'session_id': 'sid-b', 'messages': []}

    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = True
        sm.maybe_persist_session_activity('sid-b', data, min_interval_sec=60)
        sm.maybe_persist_session_activity('sid-b', data, min_interval_sec=60)

    assert mock_db.save_session.call_count == 1


def test_get_ai_auto_reply_skips_db_when_unavailable():
    import time

    mock_db = MagicMock()
    mock_db.is_available.return_value = False
    mock_db.startup_skip_reason = 'connect_failed'
    mock_db.get_global_state = MagicMock(side_effect=AssertionError("should not call DB"))

    sm._ai_auto_reply = True
    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = True
        start = time.monotonic()
        assert sm.get_ai_auto_reply() is True
        assert time.monotonic() - start < 0.1

    mock_db.get_global_state.assert_not_called()


def test_coerce_bool_normalizes_string_values():
    assert sm._coerce_bool('false', True) is False
    assert sm._coerce_bool('true', False) is True
    assert sm._coerce_bool('off', True) is False


def test_set_ai_auto_reply_pending_survives_stale_db_read():
    mock_db = MagicMock()
    mock_db.is_available.return_value = True
    mock_db.startup_skip_reason = None
    mock_db.set_global_state.return_value = False
    mock_db.get_global_state.return_value = False

    sm._ai_auto_reply = False
    sm._ai_auto_reply_pending = False
    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = True
        sm.set_ai_auto_reply(True)
        assert sm.get_ai_auto_reply() is True
        mock_db.get_global_state.assert_not_called()


def test_set_ai_auto_reply_clears_pending_after_successful_write():
    mock_db = MagicMock()
    mock_db.is_available.return_value = True
    mock_db.startup_skip_reason = None
    mock_db.set_global_state.return_value = True
    mock_db.get_global_state.return_value = False

    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = True
        sm.set_ai_auto_reply(True)
        assert sm._ai_auto_reply_pending is False
        assert sm.get_ai_auto_reply() is False
        mock_db.get_global_state.assert_called_once()


def test_resolve_database_url_from_components(monkeypatch):
    from src.services.database import resolve_database_url

    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('POSTGRES_HOST', 'ep-example.neon.tech')
    monkeypatch.setenv('POSTGRES_USER', 'user')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'p@ss')
    monkeypatch.setenv('POSTGRES_DB', 'neondb')

    url = resolve_database_url()
    assert url is not None
    assert 'ep-example.neon.tech' in url
    assert 'user' in url
    assert 'p%40ss' in url
