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
