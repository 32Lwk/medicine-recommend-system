"""Resolve typed PolicyDecision from TurnSignalSnapshot (no RouteDecision mapping)."""
from __future__ import annotations

from typing import Any, Mapping

from src.dialogue.routing.policy_types import PolicyDecision
from src.dialogue.routing.turn_signal_snapshot import TurnSignalSnapshot


def _policy_from_cues(
    sig: Any,
    *,
    evaluation_complete: bool,
    detector_source: str,
) -> PolicyDecision | None:
    """Typed PolicyDecision from already-collected cues (complete or fail-closed)."""
    if sig.controlled_or_illegal_block:
        subtype = (
            sig.policy_subtype if sig.policy_subtype in ("illegal", "controlled") else None
        )
        return PolicyDecision(
            kind="controlled_or_illegal",
            action="block",
            detector_source=detector_source,
            confidence=1.0 if evaluation_complete else 0.7,
            reason_code="controlled_or_illegal_block",
            evaluation_complete=evaluation_complete,
            subtype=subtype,
        )

    if sig.prescription_block:
        return PolicyDecision(
            kind="prescription",
            action="boundary_guidance",
            detector_source=detector_source,
            confidence=1.0 if evaluation_complete else 0.7,
            reason_code="prescription_block",
            evaluation_complete=evaluation_complete,
            subtype=sig.policy_subtype,
        )

    if sig.medical_examination:
        return PolicyDecision(
            kind="medical_examination",
            action="boundary_guidance",
            detector_source=detector_source,
            confidence=1.0 if evaluation_complete else 0.7,
            reason_code="medical_examination",
            evaluation_complete=evaluation_complete,
            subtype=None,
        )

    # H-03: ambiguous cue must survive incomplete evaluation (not drop to SF-E1).
    if sig.ambiguous_policy:
        return PolicyDecision(
            kind="ambiguous_controlled",
            action="safe_clarification",
            detector_source=detector_source,
            confidence=0.6 if evaluation_complete else 0.4,
            reason_code="unknown_controlled_policy",
            evaluation_complete=evaluation_complete,
            subtype="unknown_controlled_policy",
        )
    return None


def _policy_from_detector_text_lexical(
    snapshot: TurnSignalSnapshot,
    *,
    evaluation_complete: bool,
) -> PolicyDecision | None:
    """F-H03-R1: recover typed boundary from detector_text when cues missed.

    Only used on incomplete evaluation. Does not invent criminal defaults.
    """
    text = (getattr(snapshot, "detector_text", None) or snapshot.normalized_text or "").strip()
    if not text:
        return None
    state: dict[str, Any] = {
        "emergency_detected": False,
        "crisis_detected": False,
        "prescription_block": False,
        "controlled_or_illegal_block": False,
        "ambiguous_policy": False,
        "medical_examination": False,
        "policy_subtype": None,
    }
    from src.dialogue.routing.pre_route_signals import _latch_policy_lexical_failsafe

    _latch_policy_lexical_failsafe(text, state, allow_ambiguous_sleep=True)

    class _CueBag:
        pass

    bag = _CueBag()
    bag.controlled_or_illegal_block = bool(state["controlled_or_illegal_block"])
    bag.prescription_block = bool(state["prescription_block"])
    bag.medical_examination = bool(state["medical_examination"])
    bag.ambiguous_policy = bool(state["ambiguous_policy"])
    bag.policy_subtype = state.get("policy_subtype")
    return _policy_from_cues(
        bag,
        evaluation_complete=evaluation_complete,
        detector_source="detector_text_lexical_failsafe",
    )


def resolve_policy_decision(
    snapshot: TurnSignalSnapshot,
    *,
    triage_bag: Mapping[str, Any] | None = None,
) -> PolicyDecision:
    """Additive triage merge then pick highest-priority policy kind.

    Priority among policy kinds (after Safety already handled upstream):
      controlled_or_illegal > prescription > medical_examination
    SessionOps intent is never rewritten here.

    R19/R21 Gate B (H-03/H-04): when evaluation is incomplete / detector_errors
    exist, prefer safer terminals over generic SF-E1 when high-risk cues are
    already present OR recoverable from detector_text:
      crisis/emergency / SI paraphrase → defer_to_crisis_safety
      policy cues / lexical recover → typed PolicyDecision (boundary/block)
      otherwise → incomplete_evaluation (SF-E1 fail-closed)
    """
    snap = snapshot.with_additive(triage_bag) if triage_bag else snapshot
    sig = snap.signals
    incomplete = (not sig.evaluation_complete) or bool(sig.detector_errors)

    if incomplete:
        # H-04 / F-H04-R1: crisis cues, crisis detector failure, or soft SI
        # paraphrase on detector_text → crisis resources (never SF-E1 alone).
        crisis_eval_failed = "crisis_detector_error" in sig.detector_errors
        detector_view = (
            getattr(snap, "detector_text", None) or snap.normalized_text or ""
        )
        soft_si = False
        try:
            from src.dialogue.routing.pre_route_signals import _soft_si_paraphrase_cues

            soft_si = _soft_si_paraphrase_cues(detector_view)
        except Exception:
            soft_si = False
        if (
            sig.crisis_detected
            or sig.emergency_detected
            or crisis_eval_failed
            or soft_si
        ):
            return PolicyDecision(
                kind=None,
                action="safe_clarification",
                detector_source="preflight_fail_closed",
                confidence=0.0,
                reason_code="defer_to_crisis_safety",
                evaluation_complete=False,
                subtype=None,
            )
        # H-03: policy cues already collected → typed boundary, not SF-E1.
        cued = _policy_from_cues(
            sig,
            evaluation_complete=False,
            detector_source="preflight_fail_closed",
        )
        if cued is not None:
            return cued
        # F-H03-R1: recover from detector_text lexical markers when cues missed.
        recovered = _policy_from_detector_text_lexical(snap, evaluation_complete=False)
        if recovered is not None:
            return recovered
        return PolicyDecision(
            kind=None,
            action="safe_clarification",
            detector_source="preflight",
            confidence=0.0,
            reason_code="incomplete_evaluation",
            evaluation_complete=False,
            subtype=None,
        )

    cued = _policy_from_cues(
        sig,
        evaluation_complete=True,
        detector_source="preflight_or_triage",
    )
    if cued is not None:
        return cued

    return PolicyDecision(
        kind=None,
        action="continue",
        detector_source="none",
        confidence=1.0,
        reason_code="no_policy_hit",
        evaluation_complete=True,
        subtype=None,
    )
