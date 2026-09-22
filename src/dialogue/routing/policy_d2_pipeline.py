"""D2-b pipeline helpers: snapshot create, pure SessionOps, policy enforce hook."""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def triage_to_additive_bag(triage_result: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map triage dict → additive OR-bag for TurnSignalSnapshot.with_additive.

    Does not clear flags. Does not rewrite session_operation.
    """
    bag: dict[str, Any] = {}
    if not triage_result:
        return bag
    cat = str(triage_result.get("category") or "").strip().lower()
    sub = str(triage_result.get("subcategory") or "").strip().lower()
    if cat == "emergency" or triage_result.get("requires_immediate_action"):
        bag["emergency_detected"] = True
    if "illegal" in sub or triage_result.get("illegal_drug"):
        bag["controlled_or_illegal_block"] = True
    if "controlled" in sub:
        bag["controlled_or_illegal_block"] = True
    if "prescription" in sub or triage_result.get("prescription"):
        bag["prescription_block"] = True
    if "medical_examination" in sub or triage_result.get("medical_examination"):
        bag["medical_examination"] = True
    if triage_result.get("crisis") or triage_result.get("crisis_detected"):
        bag["crisis_detected"] = True
    if triage_result.get("security_blocked") or triage_result.get("known_attack"):
        bag["security_blocked"] = True
    return bag


def create_pipeline_snapshot(
    raw_text: str,
    *,
    turn_id: str | None = None,
    correlation_id: str | None = None,
):
    from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot

    return create_turn_signal_snapshot(
        raw_text,
        turn_id=turn_id,
        correlation_id=correlation_id,
    )


def try_pure_session_ops(
    session: Any,
    sid: Optional[str],
    snapshot,
    client: Any,
    *,
    session_ops_runner,
) -> Optional[ResponseTuple]:
    """Run SessionOps only when pure gate passes. Else None (continue pipeline)."""
    from src.dialogue.routing.turn_signal_snapshot import is_pure_session_ops

    if not is_pure_session_ops(snapshot):
        return None
    text = snapshot.normalized_text
    try:
        return session_ops_runner(
            session,
            sid,
            text,
            client,
            triage_result=None,
            phase="pure_preflight",
        )
    except Exception:
        logger.exception("pure session_ops failed; fail-closed to Safety/Policy")
        return None


def try_policy_enforcement_d2(
    session: Any,
    sid: Optional[str],
    snapshot,
    *,
    user_text: str,
    client_info: Any,
    triage_result: Optional[dict],
) -> Optional[ResponseTuple]:
    """Resolve+enforce. Return response tuple if terminal/fallback; else None."""
    from src.dialogue.routing.policy_enforce import resolve_and_enforce

    bag = triage_to_additive_bag(triage_result)
    _merged, _decision, result = resolve_and_enforce(
        snapshot,
        session=session,
        sid=sid,
        user_text=user_text,
        client_info=client_info,
        triage_bag=bag,
        triage_result=triage_result,
    )
    try:
        from src.utils.structured_logger import log_counseling_detail

        obs = dict(result.observability_fields or {})
        routing_meta = {
            "policy_enforcement_d2": True,
            "turn_id": obs.get("turn_id") or getattr(snapshot, "turn_id", None),
            "correlation_id": obs.get("correlation_id")
            or getattr(snapshot, "correlation_id", None),
            "fingerprint": obs.get("fingerprint"),
            "policy_kind": result.policy_kind,
            "policy_action": result.action,
            "detector_source": getattr(_decision, "detector_source", None),
            "handled": result.handled,
            "fallback_reason": result.fallback_reason,
            "fallback_reason_primary": obs.get("fallback_reason_primary")
            or result.fallback_reason,
            "recovery_status": obs.get("recovery_status"),
            "evaluation_complete": obs.get("evaluation_complete"),
            "detector_errors": obs.get("detector_errors"),
            "db_commit_status": result.db_commit_status or obs.get("db_commit_status"),
            "detector_view_had_evasion": obs.get("detector_view_had_evasion"),
            "rollback_ok": obs.get("rollback_ok"),
        }
        # No raw medical / user text — placeholders only (R10 M-OBS).
        log_counseling_detail(
            session_id=str(sid or ""),
            user_input="[policy_enforcement_d2]",
            response="[redacted]",
            conversation_history=[],
            routing_meta=routing_meta,
        )
    except Exception:
        logger.debug("policy_d2 observabilty log skipped", exc_info=True)

    if not result.handled:
        return None
    if result.response is None:
        return None
    return (result.response, int(result.status_code or 200))
