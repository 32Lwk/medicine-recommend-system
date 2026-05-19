"""find_existing_session と GET /api/sessions の sid 再利用テスト。"""
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


def test_api_sessions_get_reuses_existing_sid_in_cookie(client):
    import main

    existing_data = {
        "session_id": "existing-reuse-sid",
        "messages": [{"type": "user", "content": "prior"}],
        "username": "ユーザー1",
    }

    with patch("main.find_existing_session", return_value="existing-reuse-sid"):
        with patch("main.get_session_from_db", return_value=existing_data):
            client.cookies.set(main.COOKIE_NAME_SID, "brand-new-sid")
            r = client.get(
                "/api/sessions",
                headers={"User-Agent": "TestBrowser/1.0"},
            )

    assert r.status_code == 200
    assert r.json()["session_id"] == "existing-reuse-sid"
    set_cookie = r.headers.get("set-cookie", "")
    assert "existing-reuse-sid" in set_cookie
