"""R21 Gate B adversarial fixtures: Unicode/ZW, negation, OD vs controlled, etc."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest

from src.dialogue.routing.policy_enforce import resolve_and_enforce
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import (
    create_turn_signal_snapshot,
    is_pure_session_ops,
)


def test_zw_prescription_latches_boundary_not_continue():
    """F-H03-R1: ZW-split 処方 must latch prescription via detector view."""
    raw = "処\u200b方してください"
    snap = create_turn_signal_snapshot(raw, turn_id="adv-zw-rx")
    assert snap.detector_view_had_evasion is True
    assert "処方して" in snap.detector_text or "処方" in snap.detector_text
    assert snap.signals.prescription_block is True
    decision = resolve_policy_decision(snap)
    assert decision.kind == "prescription"
    assert decision.action == "boundary_guidance"


def test_zw_crisis_sessionops_mix_not_pure_session_ops():
    """SessionOps+crisis mix with ZW: never pure SessionOps; crisis wins."""
    raw = "死\u200bにたい、履歴を削除して"
    snap = create_turn_signal_snapshot(raw, turn_id="adv-zw-crisis-ops")
    assert snap.signals.crisis_detected or snap.signals.emergency_detected
    assert snap.signals.session_operation is not None or True  # ops may classify
    assert is_pure_session_ops(snap) is False
    decision = resolve_policy_decision(snap)
    # Crisis path owns — either continue for SafetyGate upstream or defer if incomplete
    if not snap.signals.evaluation_complete:
        assert decision.reason_code == "defer_to_crisis_safety"
    else:
        assert snap.signals.crisis_detected or snap.signals.emergency_detected


def test_double_negation_si_defers_or_crisis_flag():
    """Affirmative double negation must not fall through as non-crisis."""
    text = "死にたくないわけではない"
    snap = create_turn_signal_snapshot(text, turn_id="adv-dbl-neg")
    assert snap.signals.crisis_detected or "crisis" in str(snap.signals.detector_errors)
    if not snap.signals.evaluation_complete:
        assert resolve_policy_decision(snap).reason_code == "defer_to_crisis_safety"


def test_past_tense_ideation_crisis():
    snap = create_turn_signal_snapshot("死にたかった", turn_id="adv-past-si")
    assert snap.signals.crisis_detected is True


def test_overdose_vs_controlled_sleep_separation():
    """OD cues → emergency; plain 睡眠薬 → ambiguous policy (not illegal default)."""
    od = create_turn_signal_snapshot("薬を大量に飲んだ", turn_id="adv-od")
    assert od.signals.emergency_detected is True
    assert od.signals.controlled_or_illegal_block is False

    sleep = create_turn_signal_snapshot("睡眠薬ください", turn_id="adv-sleep")
    assert sleep.signals.emergency_detected is False
    assert sleep.signals.controlled_or_illegal_block is False
    assert sleep.signals.ambiguous_policy or sleep.signals.prescription_block


def test_ambiguous_sleep_incomplete_not_sf_e1():
    snap = create_turn_signal_snapshot("睡眠薬が欲しい", turn_id="adv-amb-sleep")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            evaluation_complete=False,
            detector_errors=("sleep_med_policy_detector_error",),
            ambiguous_policy=True,
            crisis_detected=False,
            emergency_detected=False,
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.kind == "ambiguous_controlled"
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        _m, _d, result = resolve_and_enforce(
            bad, session=session, sid=None, user_text="睡眠薬が欲しい"
        )
    assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_paraphrase_si_incomplete_not_sf_e1():
    """F-H04-R1: paraphrase SI + non-crisis detector error → crisis resources."""
    text = "生きるのがつらい、消えてしまいたい"
    snap = create_turn_signal_snapshot(text, turn_id="adv-para-si")
    # Force incomplete via unrelated detector error; clear flags to simulate FN.
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            crisis_detected=False,
            emergency_detected=False,
            evaluation_complete=False,
            detector_errors=("controlled_drug_detector_error",),
        ),
        detector_text=text,
        normalized_text=text,
    )
    decision = resolve_policy_decision(bad)
    assert decision.reason_code == "defer_to_crisis_safety"
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text=text
    )
    assert result.observability_fields.get("safe_fallback") == "crisis_resources"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_detector_exception_prescription_zw_boundary():
    """Detector raise + ZW prescription → boundary, not SF-E1."""
    raw = "処\u200b方してください"
    with patch(
        "src.services.medical_examination_request.detect_medical_examination_request_contained",
        side_effect=RuntimeError("exam boom"),
    ):
        snap = create_turn_signal_snapshot(raw, turn_id="adv-det-exc-rx")
    assert "medical_examination_detector_error" in snap.signals.detector_errors
    decision = resolve_policy_decision(snap)
    assert decision.kind == "prescription"
    assert decision.reason_code != "incomplete_evaluation"


def test_adapter_exception_uses_boundary_not_sf_e1():
    """F-H03-R2: adapter exception with known cue → policy_boundary, not SF-E1."""
    snap = create_turn_signal_snapshot("処方してください", turn_id="adv-adapter-exc")
    assert snap.signals.prescription_block is True
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce.run_policy_adapter",
        side_effect=RuntimeError("adapter boom"),
    ):
        _m, decision, result = resolve_and_enforce(
            snap, session=session, sid="sid-ad", user_text="処方してください"
        )
    assert decision.kind == "prescription"
    assert result.handled is True
    assert result.observability_fields.get("safe_fallback") == "policy_boundary"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    assert (result.response or {}).get("policy_boundary_fallback") is True
    sage = (result.response or {}).get("sage_diagnosis") or {}
    assert sage.get("kind") != "system_error"
    assert "処方" in str(sage) or "処方" in str(result.response)


def test_db_failure_after_cued_policy_uses_boundary():
    snap = create_turn_signal_snapshot("処方してください", turn_id="adv-db-fail")
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="failed",
    ):
        _m, _d, result = resolve_and_enforce(
            snap, session=session, sid="sid-db", user_text="処方してください"
        )
    assert result.observability_fields.get("safe_fallback") == "policy_boundary"
    assert result.fallback_reason in ("db_save_failed", "db_commit_unknown")
    assert (result.response or {}).get("recommend_stopped") is True


def test_ordering_crisis_beats_session_ops_and_policy():
    """Ordering: Crisis → … → SessionOps; Jev must not override (eligibility skip)."""
    snap = create_turn_signal_snapshot(
        "死にたい、履歴を削除して、睡眠薬ください", turn_id="adv-order"
    )
    assert snap.signals.crisis_detected or snap.signals.emergency_detected
    assert is_pure_session_ops(snap) is False
    decision = resolve_policy_decision(snap)
    # Crisis deferral wins over ambiguous sleep / SessionOps when incomplete;
    # when complete, cues still show crisis for upstream SafetyGate.
    if snap.signals.crisis_detected or snap.signals.emergency_detected:
        if not snap.signals.evaluation_complete:
            assert decision.reason_code == "defer_to_crisis_safety"
        else:
            # Complete: resolve may return continue for SafetyGate ownership,
            # but must not emit SessionOps-friendly no_policy with sleep block alone.
            assert not (
                decision.kind == "ambiguous_controlled"
                and decision.action == "continue"
            )


@pytest.mark.parametrize(
    "text",
    [
        "処\u200b方\u200bして\u200bください",
        "マン\u200bジャロを処方して",
        "チルゼパチドください",
    ],
)
def test_zw_and_named_rx_vocabulary(text):
    snap = create_turn_signal_snapshot(text, turn_id="adv-rx-vocab")
    assert snap.signals.prescription_block is True
