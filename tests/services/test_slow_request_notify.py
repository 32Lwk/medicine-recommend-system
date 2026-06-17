"""slow request notify API + feedback 連携"""
from unittest.mock import MagicMock, patch

import pytest


@patch("src.services.slow_request_notify.submit_feedback_async")
@patch("src.services.slow_request_notify.get_alert_email", return_value=None)
def test_slow_request_notify_saves_feedback_async(mock_email, mock_submit_async):
    from src.services.slow_request_notify import notify_slow_request

    notify_slow_request(
        "test-sid",
        client_ip="127.0.0.1",
        user_agent="test-agent",
        last_user_message="頭痛",
        username="ユーザー1",
        processing_status={"active": True, "current_step": "medicine_select", "percent": 42},
        client_context={"page_url": "http://localhost/"},
    )
    mock_submit_async.assert_called_once()
    kwargs = mock_submit_async.call_args.kwargs
    assert kwargs["report_type"] == "slow_request"
    assert kwargs["user_message"] == "頭痛"
    assert kwargs["metadata"]["source"] == "web"
    assert kwargs["metadata"]["event"] == "slow_request_notify"


@patch("src.services.slow_request_notify.notify_slow_request")
def test_slow_request_api(mock_notify):
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    with patch("main.get_sid", return_value="test-sid"):
        resp = client.post(
            "/api/slow-request-notify",
            json={
                "last_user_message": "頭痛",
                "client_context": {"page_url": "http://localhost/"},
            },
        )
    assert resp.status_code == 200
    mock_notify.assert_called_once()
    assert mock_notify.call_args.kwargs["last_user_message"] == "頭痛"
    assert mock_notify.call_args.kwargs["client_context"]["page_url"] == "http://localhost/"
