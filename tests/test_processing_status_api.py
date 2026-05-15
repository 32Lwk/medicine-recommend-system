"""GET /api/processing-status の API テスト"""
import os
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    import main

    with TestClient(main.app) as c:
        yield c


def test_processing_status_inactive_by_default(client):
    r = client.get("/api/processing-status")
    assert r.status_code == 200
    data = r.json()
    assert data["active"] is False
    assert data["percent"] == 0
    assert "total" in data


def test_processing_status_active_for_cookie_session(client):
    sid = "api-test-session-active"
    client.cookies.set("sid", sid)
    from src.services.processing_status import clear_processing_status, mark_processing_step

    mark_processing_step(sid, "triage")
    try:
        r = client.get("/api/processing-status")
        assert r.status_code == 200
        data = r.json()
        assert data["active"] is True
        assert data["step_id"] == "triage"
        assert data["label"]
        assert data["step"] >= 1
        assert data["percent"] > 0
    finally:
        clear_processing_status(sid)


def test_processing_status_admin_session_requires_auth(client):
    r = client.get("/api/processing-status", params={"session_id": "other-session"})
    assert r.status_code == 401


def test_processing_status_admin_session_with_auth(client):
    sid = "api-test-admin-target"
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    with patch("src.services.processing_status.get_processing_status") as mock_get:
        mock_get.return_value = {
            "active": True,
            "step_id": "medicine_select",
            "label": "お薬を選定しています",
            "step": 10,
            "total": 14,
            "percent": 71,
        }
        r = client.get(
            "/api/processing-status",
            params={"session_id": sid},
            auth=("admin", admin_password),
        )
    assert r.status_code == 200
    data = r.json()
    assert data["active"] is True
    assert data["step_id"] == "medicine_select"
    mock_get.assert_called_once_with(sid)
