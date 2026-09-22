"""BR-C01: affirmative double-negation crisis FN fixtures (medical unit).

Boundary-repair modules must not be changed by this unit.
These tests are expected to fail until the medical fix lands.
"""
from __future__ import annotations

import pytest

from src.agents.session_agent import probe_session_admin_intent
from src.core.crisis_detection import detect_crisis_keywords
from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.pre_route_signals import collect_safety_policy_signals
from src.services.jev_eligibility import (
    JevEligibilityReason,
    decide_jev_intent_eligibility,
)
from src.dialogue.routing.pre_route_signals import collect_pre_route_signals


# --- Plan: failing reproduction fixtures first ---------------------------------

BR_C01_AFFIRMATIVE_DOUBLE_NEGATION = (
    "死にたくないわけではない",
    "死にたくない訳ではない",
    "死にたくないというわけではない",
    "死にたかったことがないわけではない",
    "今は死にたくないわけではない",
    "死にたくないわけじゃない",
    "死にたくないってわけじゃない",
    "死にたくないワケではない",
)

BR_C01_TRUE_NEGATIVE_SIMPLE_NEGATION = (
    "今は死にたくない",
    "死にたくない",
)


@pytest.mark.parametrize("text", BR_C01_AFFIRMATIVE_DOUBLE_NEGATION)
def test_br_c01_double_negation_is_crisis(text: str) -> None:
    has, keywords = detect_crisis_keywords(text)
    assert has, f"FN: expected crisis for {text!r}"
    assert keywords


@pytest.mark.parametrize("text", BR_C01_TRUE_NEGATIVE_SIMPLE_NEGATION)
def test_br_c01_simple_negation_remains_non_crisis(text: str) -> None:
    has, _ = detect_crisis_keywords(text)
    assert not has, f"FP: simple negation must stay non-crisis: {text!r}"


def test_br_c01_fail_safe_token_still_crisis() -> None:
    has, _ = detect_crisis_keywords("死にたい気持ちはない")
    assert has


def test_br_c01_sessionops_cannot_bypass_double_negation() -> None:
    text = "履歴消して死にたくないわけではない"
    assert probe_session_admin_intent(text) is None
    signals = collect_pre_route_signals(text)
    decision = decide_jev_intent_eligibility(signals)
    assert decision.eligible is False
    assert decision.reason == JevEligibilityReason.DETERMINISTIC_HIGH_RISK.value
    assert decision.sessionops_fast_path_suppressed is True


def test_br_c01_counseling_cannot_swallow_double_negation() -> None:
    text = "死にたくないわけではない"
    session = {"counseling_mode": {"active": True}, "messages": []}
    decision = run_deterministic_gate(text, session, sid="br-c01-test")
    assert decision.primary_route == "Emergency"
    assert decision.primary_route != "Counseling"


def test_br_c01_mixed_euphemism_with_self_harm_still_crisis() -> None:
    text = "死にたくないわけではないがリストカットした"
    has, keywords = detect_crisis_keywords(text)
    assert has
    assert any(k in keywords for k in ("リストカット", "自傷")) or has


def test_br_c01_safety_policy_signals_mark_crisis() -> None:
    signals = collect_safety_policy_signals("死にたくないわけではない")
    assert signals.crisis_detected is True
    assert signals.evaluation_complete is True
