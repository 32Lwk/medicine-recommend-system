"""Jev IntentRouter eligibility — pure consumer of PreRouteSignals.

Contract versions (user freeze 2026-09-22):
  evaluation_contract_version = jev-intent-gate-a-v2
  eligibility_contract_version = jev-intent-eligibility-v1

Jev is an Intent Classification layer helper. Deterministic Safety,
SessionOps fast-path, and policy blocks are **out of scope** for Jev calls.

Phase 1: eligibility only gates whether shadow/eval may **call** Jev.
It must not weaken SafetyGate or change PRIMARY behavior.

This module must NOT own safety detection. Detectors live in
``src.dialogue.routing.pre_route_signals``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Optional

from src.dialogue.routing.pre_route_signals import (
    PreRouteSignals,
    collect_pre_route_signals,
)

ELIGIBILITY_CONTRACT_VERSION = "jev-intent-eligibility-v1"
EVALUATION_CONTRACT_VERSION = "jev-intent-gate-a-v2"


class JevEligibilityReason(str, Enum):
    INTENT_CLASSIFICATION_CANDIDATE = "intent_classification_candidate"
    DETERMINISTIC_HIGH_RISK = "deterministic_high_risk"
    POLICY_BLOCK = "policy_block"
    SESSIONOPS_FAST_PATH = "sessionops_fast_path"
    SIGNAL_EVALUATION_ERROR = "signal_evaluation_error"


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    reason: str
    session_operation_detected: bool = False
    sessionops_fast_path_suppressed: bool = False
    deterministic_high_risk: bool = False
    policy_block_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ineligible(
    reason: str,
    *,
    session_ops: bool = False,
    suppressed: bool = False,
    high_risk: bool = False,
    policy: bool = False,
) -> EligibilityDecision:
    return EligibilityDecision(
        eligible=False,
        reason=reason,
        session_operation_detected=session_ops,
        sessionops_fast_path_suppressed=suppressed,
        deterministic_high_risk=high_risk,
        policy_block_detected=policy,
    )


def decide_jev_intent_eligibility(signals: PreRouteSignals) -> EligibilityDecision:
    """Pure eligibility decision from shared pre-route signals.

    Priority (first match wins):
      1. signal_evaluation_error (fail-closed)
      2. deterministic_high_risk
      3. policy_block
      4. sessionops_fast_path
      5. intent_classification_candidate (eligible)
    """
    session_ops = signals.session_operation_detected

    if not signals.evaluation_complete:
        return _ineligible(
            JevEligibilityReason.SIGNAL_EVALUATION_ERROR.value,
            session_ops=session_ops,
            suppressed=session_ops,
            high_risk=signals.deterministic_high_risk,
            policy=signals.policy_block,
        )

    if signals.emergency_detected or signals.security_blocked or signals.crisis_detected:
        return _ineligible(
            JevEligibilityReason.DETERMINISTIC_HIGH_RISK.value,
            session_ops=session_ops,
            suppressed=session_ops,
            high_risk=True,
            policy=signals.policy_block,
        )

    # Use policy_block property (includes ambiguous_policy) — do not omit
    # ambiguous sleep-med / unknown-controlled from eligibility skip.
    if signals.policy_block:
        return _ineligible(
            JevEligibilityReason.POLICY_BLOCK.value,
            session_ops=session_ops,
            suppressed=session_ops,
            policy=True,
        )

    if signals.session_operation is not None:
        return _ineligible(
            JevEligibilityReason.SESSIONOPS_FAST_PATH.value,
            session_ops=True,
            suppressed=False,
        )

    return EligibilityDecision(
        eligible=True,
        reason=JevEligibilityReason.INTENT_CLASSIFICATION_CANDIDATE.value,
        session_operation_detected=False,
        sessionops_fast_path_suppressed=False,
        deterministic_high_risk=False,
        policy_block_detected=False,
    )


def _signals_from_overrides(
    text: str,
    *,
    deterministic_signals: Any = None,
    deterministic_high_risk: bool | None = None,
    policy_block_detected: bool | None = None,
    session_operation_detected: bool | None = None,
    context: Mapping[str, Any] | None = None,
) -> PreRouteSignals:
    """Build signals for the legacy wrapper API (tests / eval convenience).

    Safety axes are fail-closed: boolean overrides may only *add* high-risk /
    policy positives. They must not clear detector positives on real text
    (Worker E BE-H1).
    """
    ctx = dict(context or {})
    bag = deterministic_signals if deterministic_signals is not None else ctx.get(
        "deterministic_signals"
    )

    collected = collect_pre_route_signals(text, deterministic_signals=bag)

    emergency = collected.emergency_detected
    security = collected.security_blocked
    crisis = collected.crisis_detected
    medical = collected.medical_examination
    prescription = collected.prescription_block
    controlled = collected.controlled_or_illegal_block
    session_op = collected.session_operation

    if deterministic_high_risk is not None or "deterministic_high_risk" in ctx:
        forced = (
            bool(deterministic_high_risk)
            if deterministic_high_risk is not None
            else bool(ctx.get("deterministic_high_risk"))
        )
        if forced:
            emergency = True

    if policy_block_detected is not None or "policy_block_detected" in ctx:
        forced_policy = (
            bool(policy_block_detected)
            if policy_block_detected is not None
            else bool(ctx.get("policy_block_detected"))
        )
        if forced_policy:
            medical = True

    if session_operation_detected is not None or "session_operation_detected" in ctx:
        forced_session = (
            bool(session_operation_detected)
            if session_operation_detected is not None
            else bool(ctx.get("session_operation_detected"))
        )
        if forced_session and session_op is None:
            session_op = "override"
        elif not forced_session:
            session_op = None

    return PreRouteSignals(
        emergency_detected=emergency,
        emergency_sub_route=collected.emergency_sub_route,
        security_blocked=security,
        security_sub_route=collected.security_sub_route,
        medical_examination=medical,
        prescription_block=prescription,
        controlled_or_illegal_block=controlled,
        crisis_detected=crisis,
        session_operation=session_op,
        evaluation_complete=collected.evaluation_complete,
        detector_errors=collected.detector_errors,
    )


def is_jev_intent_router_eligible(
    user_text: str = "",
    *,
    context: Mapping[str, Any] | None = None,
    deterministic_signals: Any = None,
    deterministic_high_risk: bool | None = None,
    policy_block_detected: bool | None = None,
    session_operation_detected: bool | None = None,
) -> EligibilityDecision:
    """Convenience entry: collect shared signals then decide (no dual logic).

    Production shadow and eval should prefer ``decide_jev_intent_eligibility``
    with an already-collected ``PreRouteSignals`` when available.
    """
    ctx = dict(context or {})
    text = str(user_text or ctx.get("user_text") or ctx.get("user_input") or "")
    signals = _signals_from_overrides(
        text,
        deterministic_signals=deterministic_signals,
        deterministic_high_risk=deterministic_high_risk,
        policy_block_detected=policy_block_detected,
        session_operation_detected=session_operation_detected,
        context=ctx,
    )
    return decide_jev_intent_eligibility(signals)


def gate_flags_for_row(
    decision: EligibilityDecision,
    *,
    latency_class: Optional[str] = None,
    transport_ok: bool = True,
    eval_error: bool = False,
    fallback: bool = False,
) -> dict[str, Any]:
    """Per-row Gate membership flags (recorded on every eval/shadow row)."""
    latency_gate_eligible = bool(
        decision.eligible
        and latency_class == "warm"
        and transport_ok
        and not eval_error
        and not fallback
    )
    return {
        "jev_eligible": decision.eligible,
        "jev_eligibility_reason": decision.reason,
        "jev_attempted": False,  # caller sets True only when Jev API is invoked
        "latency_gate_eligible": latency_gate_eligible,
        "accuracy_gate_eligible": bool(decision.eligible),
        "safety_regression_eligible": True,  # product track: all cases
        "sessionops_fast_path_suppressed": decision.sessionops_fast_path_suppressed,
        "session_operation_detected": decision.session_operation_detected,
        "eligibility_contract_version": ELIGIBILITY_CONTRACT_VERSION,
        "evaluation_contract_version": EVALUATION_CONTRACT_VERSION,
    }


__all__ = [
    "ELIGIBILITY_CONTRACT_VERSION",
    "EVALUATION_CONTRACT_VERSION",
    "EligibilityDecision",
    "JevEligibilityReason",
    "decide_jev_intent_eligibility",
    "gate_flags_for_row",
    "is_jev_intent_router_eligible",
]
