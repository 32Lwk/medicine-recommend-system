"""SafetyGate"""
from unittest.mock import patch

from src.agents.safety_gate import (
    SafetyGateResult,
    _borderline_crisis_hint,
    run_safety_gate,
    run_safety_gate_pre,
)
from src.utils.chat_http_context import ChatClientInfo


def test_borderline_crisis_hint():
    assert _borderline_crisis_hint("\u6b7b\u306b\u305f\u3044\u308f\u3051\u3067\u306f\u306a\u3044") is True
    assert _borderline_crisis_hint("\u81ea\u6bba\u3057\u305f\u3044") is False


@patch("src.handlers.chat.chat_input_validator.validate_and_block_input", return_value=("ok", None))
@patch("src.handlers.chat.chat_diagnosis_handler.handle_diagnosis_if_detected", return_value=None)
@patch("src.handlers.chat.chat_inappropriate_route.handle_inappropriate_message_if_detected", return_value=None)
def test_run_safety_gate_pre_passes(_inapp, _diag, _val):
    gate, sanitized = run_safety_gate_pre(
        {},
        ChatClientInfo(client_ip="1.2.3.4", user_agent="t"),
        "sid",
        "頭痛",
        "頭痛",
    )
    assert sanitized == "ok"
    assert not gate.blocked


@patch("src.handlers.chat.chat_diagnosis_handler.handle_diagnosis_if_detected", return_value=None)
@patch("src.handlers.chat.chat_emergency_handler.handle_emergency_if_detected", return_value=None)
@patch("src.handlers.chat.chat_inappropriate_route.handle_inappropriate_message_if_detected", return_value=None)
def test_low_confidence_needs_review(_inapp, _emer, _diag):
    gate = run_safety_gate(
        {},
        ChatClientInfo(client_ip="1.2.3.4", user_agent="t"),
        "sid",
        "test",
        "test",
        triage_result={"confidence": 0.4},
        phase="full",
    )
    assert gate.needs_llm_review
    assert gate.review_reason == "low_triage_confidence"
