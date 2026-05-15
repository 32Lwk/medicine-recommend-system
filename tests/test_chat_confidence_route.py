"""confidence / Emergency ルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_confidence_route import check_triage_confidence


@patch("src.services.counseling_response.log_counseling_response")
def test_emergency_high_confidence_returns_early(mock_log):
    session = {"messages": []}
    triage = {"category": "Emergency", "confidence": 0.9}
    resp = check_triage_confidence(
        session, None, "胸が痛い", "胸が痛い", triage, MagicMock()
    )
    assert resp is not None
    assert resp[0]["status"] == "ok"
    assert session["messages"][-1].get("emergency") is True


@patch("src.services.counseling_response.log_counseling_response")
def test_low_confidence_non_emergency(mock_log):
    session = {"messages": []}
    triage = {"category": "Physical", "confidence": 0.3}
    resp = check_triage_confidence(
        session, None, "頭痛", "頭痛", triage, MagicMock()
    )
    assert resp is not None
    assert session["messages"][-1].get("requires_confirmation") is True


def test_high_confidence_continues():
    triage = {"category": "Physical", "confidence": 0.95}
    assert check_triage_confidence({}, None, "", "", triage, MagicMock()) is None
