"""processing_status サービスのユニットテスト"""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.services.processing_status import (
    PROCESSING_STEPS,
    clear_processing_status,
    get_processing_status,
    mark_processing_step,
    set_processing_language,
)


@pytest.fixture(autouse=True)
def reset_cache():
    import src.services.processing_status as ps

    with ps._lock:
        ps._cache.clear()
        ps._flow_context.clear()
        ps._last_step.clear()
        ps._last_flush_at.clear()
        ps._pending_flush.clear()
        ps._session_lang.clear()
    yield
    with ps._lock:
        ps._cache.clear()
        ps._flow_context.clear()
        ps._last_step.clear()
        ps._last_flush_at.clear()
        ps._pending_flush.clear()
        ps._session_lang.clear()


def test_mark_increases_percent_monotonically():
    sid = "test-session-1"
    mark_processing_step(sid, "validate")
    p1 = get_processing_status(sid)["percent"]
    mark_processing_step(sid, "triage")
    p2 = get_processing_status(sid)["percent"]
    mark_processing_step(sid, "medicine_select")
    p3 = get_processing_status(sid)["percent"]
    assert p1 < p2 < p3
    assert get_processing_status(sid)["step"] >= 3


def test_same_step_skipped():
    sid = "test-session-2"
    mark_processing_step(sid, "triage")
    first = get_processing_status(sid).copy()
    mark_processing_step(sid, "triage")
    second = get_processing_status(sid)
    assert first["percent"] == second["percent"]
    assert first["step_id"] == second["step_id"]


def test_clear_makes_inactive():
    sid = "test-session-3"
    mark_processing_step(sid, "validate")
    with patch("src.services.database.get_database") as mock_db:
        mock_db.return_value = MagicMock()
        clear_processing_status(sid)
    status = get_processing_status(sid)
    assert status["active"] is False
    assert status["percent"] == 0


def test_debounced_flush_single_call():
    sid = "test-session-4"
    mock_db = MagicMock()
    mock_db.connection = True
    mock_db.connection_pool = None
    with patch("src.services.database.get_database", return_value=mock_db):
        mark_processing_step(sid, "validate")
        mark_processing_step(sid, "triage")
        mark_processing_step(sid, "diagnosis")
        time.sleep(0.5)
    assert mock_db.update_processing_status_only.call_count >= 1


def test_total_steps_matches_flow():
    sid = "test-session-5"
    from src.services.processing_status import set_processing_flow

    set_processing_flow(sid, "greeting")
    mark_processing_step(sid, "finalize")
    status = get_processing_status(sid)
    assert status["total"] == 4
    assert status.get("flow_id") == "greeting"


def test_processing_language_in_status():
    sid = "test-session-6"
    set_processing_language(sid, "en")
    mark_processing_step(sid, "store")
    status = get_processing_status(sid)
    assert status["language"] == "en"
    assert status["active"] is True
