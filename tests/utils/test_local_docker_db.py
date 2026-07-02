from src.utils.local_docker_db import (
    is_local_docker_database_url,
    local_docker_auto_start_enabled,
)


def test_is_local_docker_database_url_localhost():
    assert is_local_docker_database_url(
        "postgresql://REDACTED:REDACTED@localhost:5432/medicine_recommend"
    )
    assert is_local_docker_database_url(
        "postgresql://REDACTED:REDACTED@127.0.0.1:5432/medicine_recommend"
    )


def test_is_local_docker_database_url_neon():
    assert not is_local_docker_database_url(
        "postgresql://REDACTED:REDACTED@ep-abc-pooler.neon.tech/neondb?sslmode=require"
    )
    assert not is_local_docker_database_url("")


def test_local_docker_auto_start_enabled_default(monkeypatch):
    monkeypatch.delenv("LOCAL_DOCKER_DB_AUTO", raising=False)
    assert local_docker_auto_start_enabled() is True


def test_local_docker_auto_start_disabled(monkeypatch):
    monkeypatch.setenv("LOCAL_DOCKER_DB_AUTO", "0")
    assert local_docker_auto_start_enabled() is False
