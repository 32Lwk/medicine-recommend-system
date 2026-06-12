"""DATABASE_URL 未設定時の DB ログ抑制"""
import logging

from src.services.database import DatabaseManager
from src.services import budget_guard


def test_get_connection_silent_when_intentionally_disabled(caplog):
    db = DatabaseManager()
    db.database_url = None
    db.startup_skip_reason = "no_url"

    with caplog.at_level(logging.ERROR):
        assert db.get_connection() is None
        assert db.get_global_state("TEST_KEY", default_value={"ok": True}) == {"ok": True}

    assert not any("No database connection" in r.message for r in caplog.records)


def test_budget_guard_skips_db_when_unavailable(caplog):
    db = DatabaseManager()
    db.startup_skip_reason = "no_url"

    original_db = budget_guard._db

    def _fake_db():
        return db

    budget_guard._db = _fake_db
    try:
        with caplog.at_level(logging.ERROR):
            usage = budget_guard.get_monthly_usage()
            allowed, _ = budget_guard.check_llm_allowed()
        assert usage["cost_jpy"] == 0.0
        assert allowed is True
        assert not any("No database connection" in r.message for r in caplog.records)
    finally:
        budget_guard._db = original_db


def test_is_available_false_when_connect_failed_despite_pool_object():
    db = DatabaseManager()
    db.connection_pool = object()  # プールオブジェクトだけ残る壊れた状態
    db.startup_skip_reason = "connect_failed"
    assert db.is_available() is False
    assert db.get_connection() is None


def test_mark_db_unavailable_clears_pool():
    db = DatabaseManager()
    db.connection_pool = object()
    db._mark_db_unavailable("connect_failed")
    assert db.connection_pool is None
    assert db.startup_skip_reason == "connect_failed"
