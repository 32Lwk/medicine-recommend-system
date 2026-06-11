"""緊急事案メール通知"""
from __future__ import annotations

import os
from unittest.mock import patch

from src.services.emergency_notify import (
    build_notification_status,
    is_emergency_email_enabled,
    notify_emergency_detected,
)


@patch.dict(os.environ, {"EMERGENCY_EMAIL_ENABLED": "0"}, clear=False)
def test_notify_skipped_when_disabled():
    assert is_emergency_email_enabled() is False
    assert (
        notify_emergency_detected(
            session_id="s1",
            user_message="胸が痛い",
            priority_tag="critical_medical",
            emergency_subtype="medical_self",
        )
        == "skipped_disabled"
    )


@patch.dict(os.environ, {"EMERGENCY_EMAIL_ENABLED": "1", "SMTP_HOST": "smtp.test", "SMTP_USER": "u"}, clear=False)
@patch("src.services.emergency_notify.get_alert_email", return_value="admin@example.com")
@patch("src.services.emergency_notify.get_email_notifier")
def test_notify_sent(mock_notifier, mock_addr):
    mock_notifier.return_value.send.return_value = "sent"
    status = notify_emergency_detected(
        session_id="s2",
        user_message="不審者がいる",
        priority_tag="store_high",
        emergency_subtype="store_incident",
    )
    assert status == "sent"
    mock_notifier.return_value.send.assert_called_once()
    assert mock_notifier.return_value.send.call_args[0][0] == "admin@example.com"
    assert "STORE-HIGH" in mock_notifier.return_value.send.call_args[0][1]


def test_build_notification_status():
    ns = build_notification_status("sent")
    assert ns["email"] == "sent"
    assert ns["admin"] == "pending"
