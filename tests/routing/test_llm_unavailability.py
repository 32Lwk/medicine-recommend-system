"""LLM インフラ障害検知・通知"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.confidence_gate import apply_confidence_gate
from src.services.llm_unavailability import (
    append_llm_unavailable_notice,
    get_llm_unavailable_notice_bot_for_delivery,
    is_llm_infrastructure_degraded,
    is_llm_triage_infrastructure_error,
    is_openai_infrastructure_error_text,
    mark_llm_infrastructure_degraded,
    should_block_llm_dependent_reply,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Error code: 429 - insufficient_quota", True),
        ("openai.RateLimitError: exceeded your current quota", True),
        ("rate_limit_exceeded", True),
        ("通常の低確信 reasoning", False),
        ("", False),
    ],
)
def test_is_openai_infrastructure_error_text(text, expected):
    assert is_openai_infrastructure_error_text(text) is expected


def test_is_llm_triage_infrastructure_error():
    triage = {
        "category": "Other",
        "confidence": 0.0,
        "subcategory": "error",
        "reasoning": "エラーが発生しました: Error code: 429 - insufficient_quota",
    }
    assert is_llm_triage_infrastructure_error(triage) is True
    assert is_llm_triage_infrastructure_error({"subcategory": "general_other"}) is False


@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_append_llm_unavailable_notice_once(mock_get, mock_save):
    session = {"messages": []}
    assert append_llm_unavailable_notice(session, "sid-1", user_message="頭痛い") is True
    assert session["llm_unavailable_notice_sent"] is True
    bot = session["messages"][-1]
    assert bot.get("llm_unavailable") is True
    diag = bot.get("diagnosis") or {}
    assert diag.get("render") == "sage_status"
    assert diag.get("variant") == "error"
    assert diag.get("kind") == "llm_unavailable"
    assert "詳しいAIご案内" in str(diag.get("title") or "")
    assert diag.get("sections")
    assert diag["sections"][0].get("title") == "ご利用の目安"
    assert append_llm_unavailable_notice(session, "sid-1", user_message="頭痛い") is False


@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_append_notice_even_for_greeting_when_degraded(mock_get, mock_save):
    session = {"messages": []}
    assert append_llm_unavailable_notice(session, "sid-1", user_message="やああああ") is True
    assert session["messages"]


def test_mark_llm_infrastructure_degraded_sets_flags():
    session = {"messages": []}
    with patch("src.services.llm_unavailability.append_llm_unavailable_notice", return_value=True):
        assert mark_llm_infrastructure_degraded(session, "sid-1", user_message="頭痛") is True
    assert is_llm_infrastructure_degraded(session)
    assert should_block_llm_dependent_reply(session)


def test_get_llm_unavailable_notice_bot_for_delivery():
    notice = {"type": "bot", "uuid": "n1", "diagnosis": {"render": "sage_status", "variant": "error"}}
    latest = {"type": "bot", "uuid": "b2", "diagnosis": {"render": "sage_reco"}}
    session = {"_llm_unavailable_notice_bot": notice}
    assert get_llm_unavailable_notice_bot_for_delivery(session, latest) is notice
    assert get_llm_unavailable_notice_bot_for_delivery(session, notice) is None
    assert get_llm_unavailable_notice_bot_for_delivery(session, latest) is notice


@patch("src.services.llm_unavailability.mark_llm_infrastructure_degraded", return_value=True)
@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
def test_infra_error_skips_low_confidence_clarify(mock_thresh, mock_mark):
    session = {}
    triage = {
        "category": "Other",
        "confidence": 0.0,
        "subcategory": "error",
        "reasoning": "エラーが発生しました: Error code: 429 - insufficient_quota",
    }
    early, updated = apply_confidence_gate(
        session,
        "sid",
        "頭痛い",
        "頭痛い",
        triage,
        MagicMock(),
    )
    assert early is None
    assert updated is triage
    mock_mark.assert_called_once_with(session, "sid", user_message="頭痛い")


@patch("src.services.confidence_gate._clarify_already_sent", return_value=False)
@patch("src.services.confidence_gate.is_meaningless_message", return_value=False)
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
@patch("src.services.llm_unavailability.build_llm_unavailable_bot_message")
@patch("src.services.llm_unavailability.mark_llm_infrastructure_degraded", return_value=True)
@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
def test_clarification_loop_escapes_on_second_repeat(
    mock_thresh, mock_mark, mock_bot, mock_get, mock_save, mock_retry, mock_meaningless, mock_clarify_sent
):
    from src.services.confidence_gate import build_low_confidence_clarify_message

    clarify = build_low_confidence_clarify_message("Other", "ああ")
    session = {"clarification_text_counts": {clarify: 2}}
    mock_bot.return_value = {"type": "bot", "content": "notice"}
    triage = {
        "category": "Other",
        "confidence": 0.2,
        "subcategory": "general_other",
        "reasoning": "low",
    }
    early, _ = apply_confidence_gate(
        session,
        "sid",
        "ああ",
        "ああ",
        triage,
        MagicMock(),
    )
    assert early is not None
    assert early[1] == 200
    mock_mark.assert_called_once()

