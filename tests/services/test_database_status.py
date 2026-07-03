"""get_database_status / validate_database_url_config のテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.database import (
    get_database_status,
    validate_database_url_config,
)


def test_validate_database_url_config_warns_without_pooler():
    url = "postgresql://REDACTED:REDACTED@ep-abc-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    with patch("src.services.database.resolve_database_url", return_value=url):
        warnings = validate_database_url_config()
    assert any("pooler" in w for w in warnings)


def test_validate_database_url_config_warns_channel_binding_require():
    url = (
        "postgresql://REDACTED:REDACTED@ep-abc-pooler.us-east-2.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    with patch.dict("os.environ", {"DATABASE_URL": url}, clear=False):
        with patch("src.services.database._normalize_database_url", side_effect=lambda u: u):
            warnings = validate_database_url_config()
    assert any("channel_binding" in w for w in warnings)


def test_normalize_database_url_strips_channel_binding_require():
    from src.services.database import _normalize_database_url

    url = (
        "postgresql://REDACTED:REDACTED@ep-abc-pooler.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    normalized = _normalize_database_url(url)
    assert "channel_binding" not in normalized
    assert "sslmode=require" in normalized


def test_normalize_database_url_localhost_adds_sslmode_disable():
    from src.services.database import _normalize_database_url

    url = "postgresql://REDACTED:REDACTED@localhost:5432/medicine_recommend"
    normalized = _normalize_database_url(url)
    assert "sslmode=disable" in normalized


def test_validate_database_url_config_no_pooler_warning_for_localhost():
    url = "postgresql://REDACTED:REDACTED@localhost:5432/medicine_recommend?sslmode=disable"
    with patch("src.services.database.resolve_database_url", return_value=url):
        warnings = validate_database_url_config()
    assert not any("pooler" in w for w in warnings)


def test_validate_database_url_config_ok_with_pooler():
    url = (
        "postgresql://REDACTED:REDACTED@ep-abc-123-pooler.us-east-2.aws.neon.tech/"
        "neondb?sslmode=require"
    )
    with patch("src.services.database.resolve_database_url", return_value=url):
        warnings = validate_database_url_config()
    assert not warnings


def test_get_database_status_shape():
    with (
        patch("src.services.database.resolve_database_url", return_value=""),
        patch("src.services.database.db_manager") as mock_db,
        patch("src.services.session_manager.is_db_persist_enabled", return_value=False),
    ):
        mock_db.is_available.return_value = False
        mock_db.startup_skip_reason = "no_url"
        status = get_database_status()

    assert status["available"] is False
    assert status["persist_enabled"] is False
    assert status["startup_skip_reason"] == "no_url"
    assert status["configured"] is False
    assert "config_warnings" in status
