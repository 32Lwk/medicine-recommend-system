"""Emergency dispatch / classifier のスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.emergency_classifier import classify_emergency, is_emergency_candidate
from src.handlers.chat.emergency_dispatch import dispatch_emergency, is_otc_flow_blocked


def test_is_emergency_candidate_triage_emergency():
    assert is_emergency_candidate(
        "少し気分が悪い",
        triage_result={"category": "Emergency", "confidence": 0.9},
    )


def test_is_emergency_candidate_negative():
    assert not is_emergency_candidate(
        "頭が痛い",
        triage_result={"category": "Physical", "confidence": 0.9},
    )


def test_classify_medical_from_triage():
    c = classify_emergency(
        "胸が痛い",
        triage_result={"category": "Emergency"},
    )
    assert c.subtype == "medical_self"
    assert c.priority_tag == "critical_medical"


def test_otc_hard_lock():
    session = {"medical_emergency_otc_locked": True}
    assert is_otc_flow_blocked(session) is True
    session["otc_lock_released"] = True
    assert is_otc_flow_blocked(session) is False


@patch("src.handlers.chat.emergency_dispatch._finalize_emergency_response")
@patch("src.handlers.chat.emergency_dispatch.classify_emergency")
@patch("src.agents.emergency_classifier.is_emergency_candidate", return_value=True)
def test_dispatch_medical(mock_candidate, mock_classify, mock_finalize):
    from src.agents.emergency_classifier import EmergencyClassification

    mock_classify.return_value = EmergencyClassification(
        subtype="medical_self",
        priority_tag="critical_medical",
        source="triage",
    )
    mock_finalize.return_value = ({"status": "ok", "emergency_detected": True}, 200)
    session = {"messages": [], "language": "ja"}
    resp = dispatch_emergency(
        session,
        MagicMock(),
        "sid-1",
        "胸が痛い",
        MagicMock(),
        {"category": "Emergency"},
    )
    assert resp is not None
    assert resp[0]["emergency_detected"] is True
