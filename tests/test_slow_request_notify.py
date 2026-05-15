"""slow request notify API"""
from unittest.mock import MagicMock, patch

import pytest


@patch("src.services.slow_request_notify.notify_slow_request")
def test_slow_request_api(mock_notify):
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    with patch("main.get_sid", return_value="test-sid"):
        resp = client.post(
            "/api/slow-request-notify",
            json={"last_user_message": "頭痛"},
        )
    assert resp.status_code == 200
    mock_notify.assert_called_once()
