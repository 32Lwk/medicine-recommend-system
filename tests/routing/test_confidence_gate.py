"""ConfidenceGate 単体テスト"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.confidence_gate import (    apply_confidence_gate,
    build_low_confidence_clarify_message,
    is_meaningless_message,
)


def test_is_meaningless_message():
    assert is_meaningless_message("?")
    assert is_meaningless_message("   ")
    assert is_meaningless_message("g")
    assert is_meaningless_message("ｇ")
    assert not is_meaningless_message("頭が痛い")


@pytest.mark.parametrize(
    "category,snippet",
    [
        ("Physical", "具体的な症状"),
        ("Ask", "お薬の質問"),
        ("Emotional", "気持ちの相談"),
        ("Other", "症状・お薬の目的"),
    ],
)
def test_build_low_confidence_clarify_message_category_specific(category, snippet):
    msg = build_low_confidence_clarify_message(category, "テスト入力")
    assert "テスト入力" in msg
    assert snippet in msg


@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
@patch("src.services.confidence_gate.get_recent_messages", return_value=[])
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
@patch("src.services.counseling_response.log_counseling_response")
def test_physical_low_confidence_uses_category_clarify(
    mock_log, mock_retry, mock_hist, mock_thresh
):
    session = {}
    triage = {"category": "Physical", "confidence": 0.3}
    early, _ = apply_confidence_gate(
        session,
        "sid",
        "頭が痛いかも",
        "頭が痛いかも",
        triage,
        MagicMock(),
    )
    assert early is not None
    assert "具体的な症状" in session["messages"][-1]["content"]
    assert session["messages"][-1]["requires_confirmation"] is True


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


@patch("src.services.llm_triage.llm_triage")
def test_retry_triage_delegates_to_full_llm_triage(mock_llm_triage):
    from src.services.confidence_gate import retry_triage_with_fallback_model

    mock_llm_triage.return_value = {
        "category": "Other",
        "confidence": 0.9,
        "subcategory": "store_inquiry",
    }
    client = MagicMock()
    result = retry_triage_with_fallback_model("トイレはどこ", client, conversation_history=[])

    assert result["retriage"] is True
    assert result["subcategory"] == "store_inquiry"
    mock_llm_triage.assert_called_once_with(
        "トイレはどこ",
        client,
        use_cache=False,
        conversation_history=[],
    )
