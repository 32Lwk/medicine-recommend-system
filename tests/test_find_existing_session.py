"""find_existing_session と GET /api/sessions の sid 扱いテスト。"""
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret")
    import main

    with TestClient(main.app) as c:
        yield c


def test_find_existing_session_same_ip_ua_with_messages():
    from src.services.session_manager import find_existing_session

    recent = datetime.now()
    sessions = {
        "empty-sid": {
            "client_ip": "127.0.0.1",
            "user_agent": "TestBrowser/1.0",
            "messages": [],
            "last_activity": recent,
        },
        "reuse-sid": {
            "client_ip": "127.0.0.1",
            "user_agent": "TestBrowser/1.0",
            "messages": [{"type": "user", "content": "hello"}],
            "last_activity": recent,
        },
        "other-ip": {
            "client_ip": "10.0.0.1",
            "user_agent": "TestBrowser/1.0",
            "messages": [{"type": "user", "content": "hi"}],
            "last_activity": recent,
        },
    }
    with patch("src.services.session_manager.get_all_sessions_from_db", return_value=sessions):
        found = find_existing_session("127.0.0.1", "TestBrowser/1.0")
    assert found == "reuse-sid"


def test_find_existing_session_skips_expired_window():
    from src.services.session_manager import find_existing_session, SESSION_REUSE_WINDOW

    old = datetime.now() - timedelta(seconds=SESSION_REUSE_WINDOW + 60)
    sessions = {
        "old-sid": {
            "client_ip": "127.0.0.1",
            "user_agent": "TestBrowser/1.0",
            "messages": [{"type": "user", "content": "hello"}],
            "last_activity": old,
        },
    }
    with patch("src.services.session_manager.get_all_sessions_from_db", return_value=sessions):
        found = find_existing_session("127.0.0.1", "TestBrowser/1.0")
    assert found is None


def test_api_sessions_get_keeps_cookie_sid(client):
    import main

    existing_data = {
        "session_id": "existing-reuse-sid",
        "messages": [{"type": "user", "content": "prior"}],
        "username": "ユーザー1",
    }

    with patch("main.get_session_from_db") as mock_get:
        mock_get.side_effect = lambda sid: (
            existing_data if sid == "existing-reuse-sid" else None
        )
        client.cookies.set(main.COOKIE_NAME_SID, "brand-new-sid")
        r = client.get(
            "/api/sessions",
            headers={"User-Agent": "TestBrowser/1.0"},
        )

    assert r.status_code == 200
    assert r.json()["session_id"] == "brand-new-sid"
    assert r.json()["messages_count"] == 0


def test_restore_rejects_recently_deleted_session(client):
    import main
    from src.services.session_manager import mark_session_deleted

    deleted_sid = "deleted-restore-sid"
    mark_session_deleted(deleted_sid)
    client.cookies.set(main.COOKIE_NAME_SID, deleted_sid)
    r = client.post(
        "/api/sessions/restore",
        json={"messages": [{"type": "user", "content": "should not return"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("restored") is False
    assert body.get("messages_count") == 0
    assert body.get("rejected") == "session_deleted"


def test_new_session_replaces_cookie_and_clears_old(client):
    import main

    old_data = {
        "session_id": "old-chat-sid",
        "messages": [{"type": "user", "content": "keep-me-gone"}],
        "username": "ユーザー1",
    }

    with patch("main.get_session_from_db", return_value=old_data):
        with patch("main.delete_session_by_id", return_value=True) as mock_delete:
            with patch("main.mark_session_deleted") as mock_mark_deleted:
                with patch("main.ensure_session_persisted") as mock_persist:
                    client.cookies.set(main.COOKIE_NAME_SID, "old-chat-sid")
                    r = client.post("/new_session")

    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] != "old-chat-sid"
    mock_mark_deleted.assert_called_once_with("old-chat-sid")
    mock_delete.assert_called_once_with("old-chat-sid")
    mock_persist.assert_called_once()
    set_cookie = r.headers.get("set-cookie", "")
    assert body["session_id"] in set_cookie
