"""llm_pipeline_guard の clarification ループ短絡テスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.llm_pipeline_guard import (
    clarification_loop_exceeded,
    record_clarification_text,
    try_llm_pipeline_short_circuit,
)
from src.services.confidence_gate import build_low_confidence_clarify_message


def test_clarification_loop_threshold_is_two() -> None:
    session: dict = {}
    msg = build_low_confidence_clarify_message("Other", "ああ")
    assert record_clarification_text(session, msg) == 1
    assert clarification_loop_exceeded(session, msg) is False
    assert record_clarification_text(session, msg) == 2
    assert clarification_loop_exceeded(session, msg) is True


@patch("src.services.llm_unavailability.mark_llm_infrastructure_degraded")
@patch("src.services.llm_unavailability.build_llm_unavailable_bot_message")
def test_short_circuit_on_clarification_loop(mock_bot, mock_mark) -> None:
    clarify = build_low_confidence_clarify_message("Other", "ああ")
    session = {
        "messages": [
            {"type": "bot", "content": clarify},
        ],
        "clarification_text_counts": {clarify: 2},
    }
    mock_bot.return_value = {"type": "bot", "content": "notice"}
    mock_mark.return_value = True

    result = try_llm_pipeline_short_circuit(session, "sid-1", {}, user_message="ああ")
    assert result is not None
    assert result[1] == 200
    mock_mark.assert_called_once()
