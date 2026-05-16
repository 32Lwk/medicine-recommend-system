"""ConfidenceGate 単体テスト"""
from unittest.mock import MagicMock, patch

from src.services.confidence_gate import (
    apply_confidence_gate,
    is_meaningless_message,
)


def test_is_meaningless_message():
    assert is_meaningless_message("?")
    assert is_meaningless_message("   ")
    assert not is_meaningless_message("頭が痛い")


@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
@patch("src.services.confidence_gate.get_recent_messages", return_value=[])
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
def test_low_confidence_triggers_concierge_flag(mock_retry, mock_hist, mock_thresh):
    session = {}
    triage = {"category": "Other", "confidence": 0.3, "subcategory": "general_other"}
    client = MagicMock()
    early, updated = apply_confidence_gate(
        session,
        "sid",
        "?",
        "?",
        triage,
        client,
    )
    assert early is None
    assert session.get("_confidence_gate_concierge") is True


@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
@patch("src.services.confidence_gate.get_recent_messages", return_value=[])
@patch("src.services.confidence_gate.retry_triage_with_fallback_model")
def test_retry_on_low_confidence(mock_retry, mock_hist, mock_thresh):
    mock_retry.return_value = {"category": "Ask", "confidence": 0.9}
    session = {}
    triage = {"category": "Other", "confidence": 0.4}
    early, updated = apply_confidence_gate(
        session,
        "sid",
        "風邪薬は？",
        "風邪薬は？",
        triage,
        MagicMock(),
    )
    assert early is None
    assert updated["category"] == "Ask"
    mock_retry.assert_called_once()
