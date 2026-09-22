"""BR-H01: SessionOps × short medical-examination FN fixtures.

Medical unit only — do not weaken SafetyGate; SessionOps must not win.
"""
from __future__ import annotations

import pytest

from src.agents.session_agent import probe_session_admin_intent
from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.pre_route_signals import collect_pre_route_signals
from src.services.jev_eligibility import JevEligibilityReason, decide_jev_intent_eligibility
from src.services.medical_examination_request import (
    detect_medical_examination_request_contained,
    detect_medical_examination_request_exact,
)


BR_H01_MIXED_SHORT = (
    "履歴消して診察して",
    "履歴消して診てください",
    "診察して。履歴消して",
    "記憶を消して診断して",
)


@pytest.mark.parametrize("text", BR_H01_MIXED_SHORT)
def test_br_h01_contained_detects_short_exam_in_composite(text: str) -> None:
    assert detect_medical_examination_request_exact(text) is False
    assert detect_medical_examination_request_contained(text) is True


@pytest.mark.parametrize("text", BR_H01_MIXED_SHORT)
def test_br_h01_sessionops_probe_suppressed(text: str) -> None:
    assert probe_session_admin_intent(text) is None


@pytest.mark.parametrize("text", BR_H01_MIXED_SHORT)
def test_br_h01_jev_policy_block_not_sessionops(text: str) -> None:
    d = decide_jev_intent_eligibility(collect_pre_route_signals(text))
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.POLICY_BLOCK.value
    assert d.sessionops_fast_path_suppressed is True


def test_br_h01_exact_alone_unchanged() -> None:
    assert detect_medical_examination_request_exact("診察して") is True
    assert detect_medical_examination_request_contained("診察して") is True


def test_br_h01_gate_does_not_return_sessionops_for_mixed() -> None:
    text = "履歴消して診察して"
    d = run_deterministic_gate(text, {}, "br-h01")
    # Gate may not yet own a dedicated medical-examination primary; the contract
    # here is that SessionOps must not win over the policy-blocked composite.
    assert d is None or d.primary_route != "SessionOps"
