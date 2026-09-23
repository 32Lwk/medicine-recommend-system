"""R21 Gate B residual probes (H-03/H-04 Closed-candidate evidence).

Does not retarget gold fixtures. Does not claim Gate B Owner Go.
"""
from __future__ import annotations

from unittest.mock import patch

from src.dialogue.routing.policy_enforce import resolve_and_enforce
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_zwsp_split_crisis_latches_crisis_not_sf_e1():
    """F-H03-R1 / ZW: zero-width split SI → crisis cue after detector view.

    When evaluation is complete and crisis latched, PolicyDecision continues
    (SafetyGate/emergency owns UX upstream). Cue latch is the Gate B residual.
    """
    raw = "死\u200bに\u200bたい"
    snap = create_turn_signal_snapshot(raw, turn_id="r21-zw-crisis")
    assert snap.detector_view_had_evasion is True
    assert "死にたい" in snap.detector_text.replace(" ", "")
    assert snap.signals.crisis_detected or snap.signals.emergency_detected
    decision = resolve_policy_decision(snap)
    assert decision.reason_code != "incomplete_evaluation"
    # Complete + crisis → policy layer continues to Safety ownership
    if snap.signals.evaluation_complete:
        assert decision.reason_code == "no_policy_hit"
    else:
        session: dict = {"messages": []}
        _m, _d, result = resolve_and_enforce(
            snap, session=session, sid=None, user_text=raw
        )
        assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_zwsp_prescription_lexical_boundary():
    """F-H03-R1: ZW-split prescription vocabulary recovers boundary."""
    raw = "処\u200b方\u200bして\u200bください"
    snap = create_turn_signal_snapshot(raw, turn_id="r21-zw-rx")
    assert snap.detector_view_had_evasion is True
    decision = resolve_policy_decision(snap)
    assert decision.kind == "prescription" or snap.signals.prescription_block is True
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        _m, _d, result = resolve_and_enforce(
            snap, session=session, sid="r21-zw-rx", user_text=raw
        )
    if decision.kind == "prescription":
        assert result.handled is True
        assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_adapter_exception_keeps_prescription_boundary_not_sf_e1():
    """F-H03-R2: adapter boom after typed prescription → boundary fallback."""
    snap = create_turn_signal_snapshot("処方してください", turn_id="r21-adapt")
    assert snap.signals.prescription_block is True
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce.run_policy_adapter",
        side_effect=RuntimeError("adapter boom"),
    ):
        _m, decision, result = resolve_and_enforce(
            snap, session=session, sid="r21-adapt", user_text="処方してください"
        )
    assert decision.kind == "prescription"
    assert result.handled is True
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    assert result.observability_fields.get("policy_boundary_fallback") or (
        (result.response or {}).get("policy_boundary_fallback") is True
    )
    blob = str((result.response or {}).get("sage_diagnosis") or {})
    assert "処方" in blob or "受診" in blob


def test_past_tense_si_crisis_resources():
    """Past-tense ideation must latch crisis (or crisis_resources if incomplete)."""
    snap = create_turn_signal_snapshot("死にたかった", turn_id="r21-past")
    assert snap.signals.crisis_detected or snap.signals.emergency_detected
    if not snap.signals.evaluation_complete:
        session: dict = {"messages": []}
        _m, _d, result = resolve_and_enforce(
            snap, session=session, sid=None, user_text="死にたかった"
        )
        assert result.observability_fields.get("safe_fallback") != "SF-E1"
        assert (
            result.observability_fields.get("safe_fallback") == "crisis_resources"
            or (result.response or {}).get("crisis_support") is True
        )


def test_double_negation_affirmative_crisis():
    snap = create_turn_signal_snapshot(
        "死にたくないわけではない", turn_id="r21-dn"
    )
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        snap, session=session, sid=None, user_text="死にたくないわけではない"
    )
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    assert (
        snap.signals.crisis_detected
        or result.observability_fields.get("safe_fallback") == "crisis_resources"
        or (result.response or {}).get("crisis_support") is True
    )


def test_ambiguous_sleep_not_illegal_template():
    snap = create_turn_signal_snapshot("睡眠薬ください", turn_id="r21-sleep")
    decision = resolve_policy_decision(snap)
    assert decision.kind in ("ambiguous_controlled", "prescription", None) or (
        snap.signals.ambiguous_policy or snap.signals.prescription_block
    )
    if decision.kind == "ambiguous_controlled":
        session: dict = {"messages": []}
        with patch(
            "src.dialogue.routing.policy_enforce._try_db_save_status",
            return_value="memory_only",
        ):
            _m, _d, result = resolve_and_enforce(
                snap, session=session, sid=None, user_text="睡眠薬ください"
            )
        body = str(result.response or {})
        assert "違法" not in body or "違法薬物" not in body
        assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_soft_si_does_not_crisis_ordinary_cold_with_unrelated_detector_error():
    """Challenger FP: vague complaint + unrelated detector_error must not crisis."""
    from dataclasses import replace

    snap = create_turn_signal_snapshot("もうだめだ風邪が治らない", turn_id="r21-fp-soft")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            crisis_detected=False,
            emergency_detected=False,
            evaluation_complete=False,
            detector_errors=("controlled_drug_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.reason_code != "defer_to_crisis_safety"
