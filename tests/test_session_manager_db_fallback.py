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
    yield
    sm._all_sessions.clear()
    sm._db_persist_enabled = None
    sm._memory_fallback_logged = False
    sm._last_db_persist_at.clear()


def test_save_session_to_db_logs_memory_fallback_once(caplog):
    mock_db = MagicMock()
    mock_db.connection = None
    mock_db.connection_pool = None
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
    mock_db.connection_pool = None
    data = {'session_id': 'sid-a', 'messages': []}

    with patch.object(sm, 'get_database', return_value=mock_db):
        sm.maybe_persist_session_activity('sid-a', data)
        sm.maybe_persist_session_activity('sid-a', data)

    mock_db.save_session.assert_not_called()
    assert sm._all_sessions['sid-a'] is data


def test_maybe_persist_throttles_db_writes():
    mock_db = MagicMock()
    mock_db.connection_pool = object()
    mock_db.save_session.return_value = True
    data = {'session_id': 'sid-b', 'messages': []}

    with patch.object(sm, 'get_database', return_value=mock_db):
        sm._db_persist_enabled = True
        sm.maybe_persist_session_activity('sid-b', data, min_interval_sec=60)
        sm.maybe_persist_session_activity('sid-b', data, min_interval_sec=60)

    assert mock_db.save_session.call_count == 1


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
