"""OPENAI 未設定時の llm_unavailable 早期ガード。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.llm_unavailability import (
    is_llm_configuration_error_text,
    is_llm_triage_infrastructure_error,
    try_respond_when_openai_unconfigured,
)


def test_configuration_error_text_detected():
    assert is_llm_configuration_error_text("OPENAI_API_KEY not configured") is True
    assert is_llm_configuration_error_text("random failure") is False


def test_triage_error_with_missing_key_is_infrastructure():
    triage = {
        "category": "Other",
        "subcategory": "error",
        "confidence": 0.0,
        "reasoning": "エラーが発生しました: OPENAI_API_KEY not configured",
    }
    assert is_llm_triage_infrastructure_error(triage) is True


@patch("src.services.llm_unavailability.is_openai_configured", return_value=False)
def test_try_respond_appends_notice(mock_configured):
    session = {"messages": [{"type": "user", "content": "頭痛"}]}
    body, code = try_respond_when_openai_unconfigured(session, "web:test", user_message="頭痛")
    assert code == 200
    assert body["message_count"] == 2
    assert session["messages"][-1]["type"] == "bot"
    assert (session["messages"][-1].get("diagnosis") or {}).get("kind") == "llm_unavailable"
