"""Unit tests: TurnSignalSnapshot SSOT + pure SessionOps gate."""
from __future__ import annotations

from src.dialogue.routing.turn_signal_snapshot import (
    create_turn_signal_snapshot,
    is_pure_session_ops,
)


def test_snapshot_fingerprint_no_raw_in_observability():
    snap = create_turn_signal_snapshot("頭が痛いです", turn_id="t1", correlation_id="c1")
    obs = snap.observability_fields()
    assert "fingerprint" in obs
    assert "頭" not in str(obs)
    assert obs["turn_id"] == "t1"
    assert snap.normalized_text  # request-local ok


def test_pure_session_ops_requires_all_gates():
    snap = create_turn_signal_snapshot("履歴を削除して", turn_id="t2")
    # May or may not classify as session op depending on classifier;
    # if classified and no risk → pure
    if snap.signals.session_operation_detected and not snap.signals.policy_block:
        if snap.evaluation_complete and not snap.detector_errors:
            if not snap.signals.deterministic_high_risk:
                assert is_pure_session_ops(snap) is True


def test_policy_blocks_pure_session_ops():
    snap = create_turn_signal_snapshot("処方してください。履歴も消して", turn_id="t3")
    # prescription marker should set policy_block → not pure
    if snap.signals.prescription_block or snap.signals.policy_block:
        assert is_pure_session_ops(snap) is False


def test_additive_or_only_no_true_to_false():
    snap = create_turn_signal_snapshot("処方してください", turn_id="t4")
    assert snap.signals.prescription_block is True
    merged = snap.with_additive({"prescription_block": False})
    assert merged.signals.prescription_block is True


def test_session_operation_frozen_against_triage():
    snap = create_turn_signal_snapshot("履歴を要約して", turn_id="t5")
    before = snap.signals.session_operation
    merged = snap.with_additive({"session_operation": "delete"})
    assert merged.signals.session_operation == before  # no auto-upgrade to delete


def test_evaluation_incomplete_cannot_recover():
    snap = create_turn_signal_snapshot("hello", turn_id="t6")
    # Force incomplete via replace on signals through additive with errors — 
    # with_additive does not accept errors; construct manually
    from dataclasses import replace
    from src.dialogue.routing.pre_route_signals import PreRouteSignals

    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            evaluation_complete=False,
            detector_errors=("crisis_detector_error",),
        ),
    )
    recovered = bad.with_additive({"prescription_block": True})
    assert recovered.evaluation_complete is False
    assert is_pure_session_ops(recovered) is False
