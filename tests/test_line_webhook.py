"""
LINE Webhook 環境構築の回帰テスト（署名検証・有効フラグのみ）
"""
import base64
import hashlib
import hmac
import importlib
import json

import pytest
from starlette.testclient import TestClient


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _reload_line_modules(monkeypatch, *, enabled: bool, secret: str | None) -> None:
    """.env の override を避け、LINE 設定だけをテスト用に反映する。"""
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("LINE_WEBHOOK_ENABLED", "true" if enabled else "false")
    if secret is None:
        monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
    else:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", secret)
    monkeypatch.setattr("config.app_config.load_env", lambda: False)

    import config.line_config as line_config
    import main
    import src.handlers.line.line_webhook as line_webhook

    importlib.reload(line_config)
    importlib.reload(line_webhook)
    importlib.reload(main)


@pytest.fixture()
def client(monkeypatch):
    _reload_line_modules(monkeypatch, enabled=False, secret=None)
    import main

    with TestClient(main.app) as c:
        yield c


def test_line_webhook_status_disabled(client):
    r = client.get("/line/webhook/status")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data["channel_secret_configured"] is False


def test_line_webhook_disabled_returns_503(client):
    r = client.post("/line/webhook", content=b"{}", headers={"X-Line-Signature": "x"})
    assert r.status_code == 503


def test_line_webhook_enabled_without_secret_returns_503(monkeypatch):
    _reload_line_modules(monkeypatch, enabled=True, secret=None)
    import main

    with TestClient(main.app) as c:
        r = c.post("/line/webhook", content=b"{}", headers={"X-Line-Signature": "x"})
        assert r.status_code == 503


def test_line_webhook_invalid_signature_returns_401(monkeypatch):
    _reload_line_modules(monkeypatch, enabled=True, secret="test-channel-secret")
    import main

    body = json.dumps({"events": []}).encode("utf-8")
    with TestClient(main.app) as c:
        r = c.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "invalid", "Content-Type": "application/json"},
        )
        assert r.status_code == 401


def test_line_webhook_valid_signature_returns_200(monkeypatch):
    secret = "test-channel-secret"
    _reload_line_modules(monkeypatch, enabled=True, secret=secret)
    import main

    body = json.dumps({"events": [{"type": "message"}]}).encode("utf-8")
    sig = _sign(body, secret)
    with TestClient(main.app) as c:
        r = c.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": sig, "Content-Type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "events_received": 1}


def test_line_webhook_text_event_schedules_background(monkeypatch):
    secret = "test-channel-secret"
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-access-token")
    _reload_line_modules(monkeypatch, enabled=True, secret=secret)
    import main
    import src.handlers.line.line_dedup as line_dedup
    import src.handlers.line.line_webhook as line_webhook

    line_dedup.reset_dedup_cache_for_tests()
    scheduled = []

    def fake_schedule(events):
        scheduled.extend(events)

    monkeypatch.setattr(line_webhook, "_schedule_line_events", fake_schedule)

    event = {
        "type": "message",
        "webhookEventId": "evt-test-1",
        "message": {"type": "text", "text": "頭が痛い"},
        "source": {"type": "user", "userId": "Utest"},
        "replyToken": "token",
    }
    body = json.dumps({"events": [event]}).encode("utf-8")
    sig = _sign(body, secret)
    with TestClient(main.app) as c:
        r = c.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": sig, "Content-Type": "application/json"},
        )
        assert r.status_code == 200
    assert len(scheduled) == 1
    assert scheduled[0]["type"] == "message"
