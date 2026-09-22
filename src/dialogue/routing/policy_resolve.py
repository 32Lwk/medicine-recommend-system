"""Resolve typed PolicyDecision from TurnSignalSnapshot (no RouteDecision mapping)."""
from __future__ import annotations

from typing import Any, Mapping

from src.dialogue.routing.policy_types import PolicyDecision
from src.dialogue.routing.turn_signal_snapshot import TurnSignalSnapshot


def resolve_policy_decision(
    snapshot: TurnSignalSnapshot,
    *,
    triage_bag: Mapping[str, Any] | None = None,
) -> PolicyDecision:
    """Additive triage merge then pick highest-priority policy kind.

    Priority among policy kinds (after Safety already handled upstream):
      controlled_or_illegal > prescription > medical_examination
    SessionOps intent is never rewritten here.
    """
    snap = snapshot.with_additive(triage_bag) if triage_bag else snapshot
    sig = snap.signals

    if not sig.evaluation_complete or sig.detector_errors:
        return PolicyDecision(
            kind=None,
            action="safe_clarification",
            detector_source="preflight",
            confidence=0.0,
            reason_code="incomplete_evaluation",
            evaluation_complete=False,
            subtype=None,
        )

    if sig.controlled_or_illegal_block:
        subtype = sig.policy_subtype if sig.policy_subtype in ("illegal", "controlled") else None
        return PolicyDecision(
            kind="controlled_or_illegal",
            action="block",
            detector_source="preflight_or_triage",
            confidence=1.0,
            reason_code="controlled_or_illegal_block",
            evaluation_complete=True,
            subtype=subtype,
        )

    if sig.prescription_block:
        return PolicyDecision(
            kind="prescription",
            action="boundary_guidance",
            detector_source="preflight_or_triage",
            confidence=1.0,
            reason_code="prescription_block",
            evaluation_complete=True,
            subtype=sig.policy_subtype,
        )

    if sig.medical_examination:
        return PolicyDecision(
            kind="medical_examination",
            action="boundary_guidance",
            detector_source="preflight_or_triage",
            confidence=1.0,
            reason_code="medical_examination",
            evaluation_complete=True,
            subtype=None,
        )

    if sig.ambiguous_policy:
        return PolicyDecision(
            kind="ambiguous_controlled",
            action="safe_clarification",
            detector_source="preflight_or_triage",
            confidence=0.6,
            reason_code="unknown_controlled_policy",
            evaluation_complete=True,
            subtype="unknown_controlled_policy",
        )

    return PolicyDecision(
        kind=None,
        action="continue",
        detector_source="none",
        confidence=1.0,
        reason_code="no_policy_hit",
        evaluation_complete=True,
        subtype=None,
    )
