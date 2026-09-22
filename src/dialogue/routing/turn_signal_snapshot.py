"""Immutable TurnSignalSnapshot SSOT for A-3/D2-b preflight (R7)."""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, replace
from typing import Any, Mapping

from src.dialogue.routing.canonical_normalize import NORM_ALGO_VERSION
from src.dialogue.routing.detector_text_view import DETECTOR_VIEW_VERSION, prepare_text_views
from src.dialogue.routing.pre_route_signals import PreRouteSignals, collect_pre_route_signals


def _fingerprint(normalized: str) -> str:
    payload = f"{NORM_ALGO_VERSION}\0{normalized}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class TurnSignalSnapshot:
    signals: PreRouteSignals
    normalized_text_fingerprint: str
    norm_algo_version: str
    turn_id: str
    correlation_id: str
    normalized_text: str  # request-local only; never log/observability copy
    detector_text: str = ""  # request-local detector comparison view; not for display logs
    detector_view_version: str = DETECTOR_VIEW_VERSION
    detector_view_had_evasion: bool = False

    @property
    def detector_errors(self) -> tuple[str, ...]:
        return self.signals.detector_errors

    @property
    def evaluation_complete(self) -> bool:
        return bool(self.signals.evaluation_complete)

    def with_additive(self, bag: Mapping[str, Any] | None) -> TurnSignalSnapshot:
        """OR-merge triage/safety flags. Never clears True→False or recovers incomplete."""
        from src.dialogue.routing.pre_route_signals import merge_additive_bag

        if not bag:
            return self
        sig = self.signals
        state: dict[str, Any] = {
            "emergency_detected": sig.emergency_detected,
            "emergency_sub_route": sig.emergency_sub_route,
            "security_blocked": sig.security_blocked,
            "security_sub_route": sig.security_sub_route,
            "medical_examination": sig.medical_examination,
            "prescription_block": sig.prescription_block,
            "controlled_or_illegal_block": sig.controlled_or_illegal_block,
            "crisis_detected": sig.crisis_detected,
            "session_operation": sig.session_operation,
            "ambiguous_policy": sig.ambiguous_policy,
        }
        errors = list(sig.detector_errors)
        complete = sig.evaluation_complete
        before_session_op = state["session_operation"]
        merge_additive_bag(state, bag)
        state["session_operation"] = before_session_op

        state["emergency_detected"] = bool(sig.emergency_detected or state["emergency_detected"])
        state["security_blocked"] = bool(sig.security_blocked or state["security_blocked"])
        state["medical_examination"] = bool(sig.medical_examination or state["medical_examination"])
        state["prescription_block"] = bool(sig.prescription_block or state["prescription_block"])
        state["controlled_or_illegal_block"] = bool(
            sig.controlled_or_illegal_block or state["controlled_or_illegal_block"]
        )
        state["crisis_detected"] = bool(sig.crisis_detected or state["crisis_detected"])
        state["ambiguous_policy"] = bool(sig.ambiguous_policy or state.get("ambiguous_policy"))
        if sig.emergency_sub_route and not state.get("emergency_sub_route"):
            state["emergency_sub_route"] = sig.emergency_sub_route
        if sig.security_sub_route and not state.get("security_sub_route"):
            state["security_sub_route"] = sig.security_sub_route

        new_complete = complete and len(errors) == 0
        new_signals = PreRouteSignals(
            emergency_detected=bool(state["emergency_detected"]),
            emergency_sub_route=state.get("emergency_sub_route"),
            security_blocked=bool(state["security_blocked"]),
            security_sub_route=state.get("security_sub_route"),
            medical_examination=bool(state["medical_examination"]),
            prescription_block=bool(state["prescription_block"]),
            controlled_or_illegal_block=bool(state["controlled_or_illegal_block"]),
            crisis_detected=bool(state["crisis_detected"]),
            session_operation=before_session_op,
            ambiguous_policy=bool(state["ambiguous_policy"]),
            policy_subtype=sig.policy_subtype,
            evasion_fail_closed=sig.evasion_fail_closed,
            evaluation_complete=new_complete,
            detector_errors=tuple(errors),
        )
        return replace(self, signals=new_signals)

    def observability_fields(self) -> dict[str, Any]:
        s = self.signals
        return {
            "turn_id": self.turn_id,
            "correlation_id": self.correlation_id,
            "fingerprint": self.normalized_text_fingerprint,
            "norm_algo_version": self.norm_algo_version,
            "detector_view_version": self.detector_view_version,
            "detector_view_had_evasion": self.detector_view_had_evasion,
            "evaluation_complete": s.evaluation_complete,
            "detector_errors": list(s.detector_errors),
            "emergency_detected": s.emergency_detected,
            "security_blocked": s.security_blocked,
            "crisis_detected": s.crisis_detected,
            "medical_examination": s.medical_examination,
            "prescription_block": s.prescription_block,
            "controlled_or_illegal_block": s.controlled_or_illegal_block,
            "ambiguous_policy": s.ambiguous_policy,
            "policy_subtype": s.policy_subtype,
            "evasion_fail_closed": s.evasion_fail_closed,
            "session_operation": s.session_operation,
            "policy_block": s.policy_block,
            "deterministic_high_risk": s.deterministic_high_risk,
        }


def create_turn_signal_snapshot(
    raw_text: str,
    *,
    turn_id: str | None = None,
    correlation_id: str | None = None,
    deterministic_signals: Any = None,
) -> TurnSignalSnapshot:
    """Single-collect preflight snapshot. Call once per turn."""
    tid = turn_id or str(uuid.uuid4())
    cid = correlation_id or tid
    canonical, dview = prepare_text_views(raw_text)
    signals = collect_pre_route_signals(
        canonical,
        deterministic_signals=deterministic_signals,
        detector_text=dview.text,
        evasion_fail_closed=dview.had_evasion_residue,
    )
    return TurnSignalSnapshot(
        signals=signals,
        normalized_text_fingerprint=_fingerprint(canonical),
        norm_algo_version=NORM_ALGO_VERSION,
        turn_id=tid,
        correlation_id=cid,
        normalized_text=canonical,
        detector_text=dview.text,
        detector_view_version=dview.version,
        detector_view_had_evasion=dview.had_evasion_residue,
    )


def is_pure_session_ops(snapshot: TurnSignalSnapshot) -> bool:
    """Pure SessionOps only when all gates pass (R7-A fail-closed)."""
    s = snapshot.signals
    if not s.evaluation_complete:
        return False
    if s.detector_errors:
        return False
    if s.deterministic_high_risk:
        return False
    if s.policy_block:
        return False
    if s.evasion_fail_closed:
        return False
    if snapshot.detector_view_had_evasion and s.session_operation_detected:
        return False
    if not s.session_operation_detected:
        return False
    return True
