"""processing_status 読み取りキャッシュ（DB fallback 削減）"""
from unittest.mock import MagicMock, patch

from src.services.processing_status import (
    _pop_read_cache,
    get_processing_status,
    mark_processing_step,
)


def test_read_cache_serves_other_worker_without_db():
    sid = "read-cache-session"
    mark_processing_step(sid, "validate")

    import src.services.processing_status as ps

    with ps._lock:
        ps._cache.pop(sid, None)

    mock_db = MagicMock()
    mock_db.connection = True
    mock_db.connection_pool = None
    with patch("src.services.database.get_database", return_value=mock_db):
        status = get_processing_status(sid)

    assert status["active"] is True
    assert status["step_id"] == "validate"
    mock_db.get_processing_status_only.assert_not_called()
    _pop_read_cache(sid)


def test_inactive_read_cache_avoids_repeated_db_hits():
    sid = "inactive-cache-session"
    mock_db = MagicMock()
    mock_db.connection = True
    mock_db.connection_pool = None
    mock_db.get_processing_status_only.return_value = None

    with patch("src.services.database.get_database", return_value=mock_db):
        first = get_processing_status(sid)
        second = get_processing_status(sid)

    assert first["active"] is False
    assert second["active"] is False
    assert mock_db.get_processing_status_only.call_count == 1
    _pop_read_cache(sid)
