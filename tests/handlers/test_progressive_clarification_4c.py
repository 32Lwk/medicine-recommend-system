"""p3-correction-sessionops 4c: progressive clarification（UX_PROGRESSIVE_CLARIFICATION）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.llm_pipeline_guard import (
    count_prior_clarification_bots,
    get_clarification_attempt,
    record_clarification_text,
    try_llm_pipeline_short_circuit,
)
from src.services.confidence_gate import (
    apply_confidence_gate,
    build_low_confidence_clarify_message,
)


def test_tier1_and_tier2_messages_differ() -> None:
    t1 = build_low_confidence_clarify_message("Physical", "ああ", tier=1)
    t2 = build_low_confidence_clarify_message("Physical", "ああ", tier=2)
    assert t1 != t2
    assert "頭痛、発熱" in t1
    assert "咳・鼻水" in t2


def test_count_prior_clarification_from_messages() -> None:
    clarify = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    session = {
        "messages": [
            {"type": "user", "content": "ああ"},
            {"type": "bot", "content": clarify},
        ],
    }
    assert count_prior_clarification_bots(session) == 1
    assert get_clarification_attempt(session) == 2


def test_clarification_text_counts_increase_attempt() -> None:
    session: dict = {"messages": []}
    msg = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    assert get_clarification_attempt(session) == 1
    record_clarification_text(session, msg)
    assert get_clarification_attempt(session) == 2


@patch("src.services.confidence_gate._clarify_already_sent", return_value=False)
@patch("src.services.confidence_gate.is_meaningless_message", return_value=False)
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
def test_flag_on_second_attempt_uses_tier2(
    _thresh, _get, _save, _retry, _meaningless, _clarify_sent, monkeypatch
) -> None:
    monkeypatch.setenv("UX_PROGRESSIVE_CLARIFICATION", "true")
    tier1 = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    session = {
        "messages": [
            {"type": "user", "content": "ああ"},
            {"type": "bot", "content": tier1},
        ],
        "clarification_text_counts": {tier1: 1},
    }
    triage = {"category": "Other", "confidence": 0.2, "subcategory": "general_other"}
    early, _ = apply_confidence_gate(
        session, "sid", "ああ", "ああ", triage, MagicMock(),
    )
    assert early is not None
    bot_text = session["messages"][-1]["content"]
    assert "もう一度整理" in bot_text
    assert bot_text != tier1


@patch("src.services.confidence_gate._clarify_already_sent", return_value=False)
@patch("src.services.confidence_gate.is_meaningless_message", return_value=False)
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
@patch("src.services.llm_unavailability.build_llm_unavailable_bot_message")
@patch("src.services.llm_unavailability.mark_llm_infrastructure_degraded", return_value=True)
@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
def test_flag_on_third_attempt_escapes(
    _thresh, _mark, mock_bot, _get, _save, _retry, _meaningless, _clarify_sent, monkeypatch
) -> None:
    monkeypatch.setenv("UX_PROGRESSIVE_CLARIFICATION", "true")
    tier1 = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    tier2 = build_low_confidence_clarify_message("Other", "ああ", tier=2)
    session = {
        "messages": [
            {"type": "bot", "content": tier1},
            {"type": "bot", "content": tier2},
        ],
        "clarification_text_counts": {tier1: 1, tier2: 1},
    }
    mock_bot.return_value = {"type": "bot", "content": "notice", "diagnosis": {"kind": "llm_unavailable"}}
    triage = {"category": "Other", "confidence": 0.2}
    early, _ = apply_confidence_gate(
        session, "sid", "ああ", "ああ", triage, MagicMock(),
    )
    assert early is not None
    _mark.assert_called_once()


@patch("src.services.confidence_gate._clarify_already_sent", return_value=False)
@patch("src.services.confidence_gate.is_meaningless_message", return_value=False)
@patch("src.services.confidence_gate.retry_triage_with_fallback_model", return_value=None)
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
@patch("src.services.confidence_gate.triage_confidence_threshold", return_value=0.75)
def test_flag_off_keeps_tier1(
    _thresh, _get, _save, _retry, _meaningless, _clarify_sent, monkeypatch
) -> None:
    monkeypatch.delenv("UX_PROGRESSIVE_CLARIFICATION", raising=False)
    tier1 = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    session = {
        "messages": [{"type": "bot", "content": tier1}],
        "clarification_text_counts": {tier1: 1},
    }
    triage = {"category": "Other", "confidence": 0.2}
    early, _ = apply_confidence_gate(
        session, "sid", "ああ", "ああ", triage, MagicMock(),
    )
    assert early is not None
    assert session["messages"][-1]["content"] == tier1


@patch("src.services.llm_unavailability.mark_llm_infrastructure_degraded")
@patch("src.services.llm_unavailability.build_llm_unavailable_bot_message")
def test_short_circuit_progressive_third_attempt(mock_bot, mock_mark, monkeypatch) -> None:
    monkeypatch.setenv("UX_PROGRESSIVE_CLARIFICATION", "true")
    tier1 = build_low_confidence_clarify_message("Other", "ああ", tier=1)
    tier2 = build_low_confidence_clarify_message("Other", "ああ", tier=2)
    session = {
        "messages": [
            {"type": "bot", "content": tier1},
            {"type": "bot", "content": tier2},
        ],
    }
    mock_bot.return_value = {"type": "bot", "content": "notice"}
    result = try_llm_pipeline_short_circuit(session, "sid", {}, user_message="ああ")
    assert result is not None
    mock_mark.assert_called_once()
