"""GET /api/sessions の遅延 persist と PATCH activity の契約テスト。"""
import os

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    import main

    with TestClient(main.app) as c:
        yield c


def test_get_sessions_does_not_create_db_row_without_db(client):
    """DB 未接続時でも GET は 200 を返し、行を増やさない（メモリのみ）。"""
    r = client.get("/api/sessions")
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert body.get("messages_count", 0) == 0


def test_patch_activity_returns_204_when_no_db_row(client):
    r = client.patch("/api/sessions/activity")
    assert r.status_code == 204


def test_post_new_session_does_not_require_db_username_only(client):
    r = client.post("/new_session")
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "username" in body
