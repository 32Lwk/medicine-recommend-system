"""R11 local: SessionOps×prescription / exam vocabulary drift guards."""
from __future__ import annotations

from src.dialogue.routing.pre_route_signals import (
    PreRouteSignals,
    collect_safety_policy_signals,
)
from src.dialogue.routing.turn_signal_snapshot import (
    create_turn_signal_snapshot,
    is_pure_session_ops,
)
from src.services.jev_eligibility import decide_jev_intent_eligibility
from src.services.medical_examination_request import (
    detect_medical_examination_request_contained,
)


def test_prescription_markers_cover_triage_taxonomy_mix():
    for text in (
        "履歴消して、処方薬を教えて",
        "履歴消して、マンジャロをください",
        "チルゼパチドを処方して",
    ):
        sig = collect_safety_policy_signals(text)
        assert sig.prescription_block is True, text


def test_exam_contained_covers_ishi_mitehoshii_mix():
    assert detect_medical_examination_request_contained("履歴消して、医者に見てほしい")
    assert detect_medical_examination_request_contained("診療お願いします")
    sig = collect_safety_policy_signals("履歴消して、医者に見てほしい")
    assert sig.medical_examination is True


def test_sessionops_mix_prescription_not_pure():
    snap = create_turn_signal_snapshot("履歴消して、処方薬を教えて")
    assert snap.signals.prescription_block is True
    assert is_pure_session_ops(snap) is False


def test_sessionops_mix_exam_ishi_not_pure():
    snap = create_turn_signal_snapshot("履歴消して、医者に見てほしい")
    assert snap.signals.medical_examination is True
    assert is_pure_session_ops(snap) is False


def test_ambiguous_policy_makes_jev_ineligible():
    sig = PreRouteSignals(ambiguous_policy=True, evaluation_complete=True)
    decision = decide_jev_intent_eligibility(sig)
    assert decision.eligible is False
    assert decision.reason == "policy_block"
