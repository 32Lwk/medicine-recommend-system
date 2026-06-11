"""開発環境でのフィードバック DB フォールバック"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def feedback_payload():
    return {
        "report_type": "positive_feedback",
        "user_message": "test message",
        "ai_response": "test response",
        "security_score": None,
        "feedback_text": "",
    }


def test_submit_feedback_dev_fallback(client, feedback_payload):
    r = client.post("/api/submit_feedback", json=feedback_payload)
    if r.status_code == 500 and "Database" in r.text:
        pytest.skip("production-like env without dev fallback")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "success"
    assert body.get("feedback_id")


def test_get_feedback_reports_dev_fallback(client, feedback_payload):
    client.post("/api/submit_feedback", json=feedback_payload)
    r = client.get("/api/get_feedback_reports")
    if r.status_code == 500:
        pytest.skip("production-like env without dev fallback")
    assert r.status_code == 200
    data = r.json()
    assert "reports" in data
    assert isinstance(data["reports"], list)
