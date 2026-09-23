"""Apply PolicyDecision via content-only adapters + MutationPlan (A-3/D2).

Never maps PolicyDecision onto RouteDecision.primary_route.
Adapters must not mutate session; this module owns mutation + persistence.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from src.dialogue.routing.policy_adapters import run_policy_adapter
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.policy_types import (
    AdapterResult,
    MutationPlan,
    PolicyDecision,
    PolicyEnforcementResult,
)
from src.dialogue.routing.turn_signal_snapshot import TurnSignalSnapshot

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

# R7-E: SF-E1-NM frozen/disabled — always SF-E1. Do not claim broad "記録未変更".
SF_E1_NM_ENABLED = False
_SF_E1_NM_SUFFIX = "今回の操作では履歴や記録内容は変更されていません。"  # frozen; unused while disabled

# Request-local deduplication only (R7-F). NOT durable exactly-once.
_REQUEST_LOCAL_DEDUP_KEY = "_policy_enforcement_d2_request_local_dedup"

_CHECKPOINT_KEYS = (
    "messages",
    "inappropriate_requests",
    "counseling_mode",
    "illegal_drug_block",
    "pending_memory_delete",
    "counseling_symptom_type",
    "counseling_questions",
    _REQUEST_LOCAL_DEDUP_KEY,
    # legacy alias if older turns wrote it
    "_policy_enforcement_d2_receipt",
)


@dataclass(frozen=True)
class CheckpointEntry:
    existed: bool
    value: Any


@dataclass
class SessionCheckpoint:
    entries: dict[str, CheckpointEntry]
    modified_existed: bool
    modified_value: Any

    def deep_equals_session(self, session: Any) -> bool:
        for key, entry in self.entries.items():
            if entry.existed:
                if key not in session:
                    return False
                if session.get(key) != entry.value:
                    return False
            else:
                if key in session:
                    return False
        if self.modified_existed:
            if not hasattr(session, "modified"):
                return False
            if getattr(session, "modified", None) != self.modified_value:
                return False
        return True


def build_sf_e1_response(*, no_mutation_claim: bool = False) -> dict[str, Any]:
    """SF-E1 only (R7-E: NM disabled). Never reuse emergency/drug/exam templates."""
    from src.services.status_diagnosis_builder import build_system_error_status

    del no_mutation_claim  # NM frozen — argument kept for API compat
    status = build_system_error_status()
    return status.to_client_dict()


def build_crisis_resources_response(*, language: str = "ja") -> dict[str, Any]:
    """Crisis resources UX for fail-closed disposition (H-04). Not SF-E1."""
    from src.core.crisis_detection import get_crisis_support_resources
    from src.services.status_diagnosis_builder import build_crisis_status

    resources = get_crisis_support_resources(language)
    status = build_crisis_status(
        resources["message"],
        resources=resources.get("resources"),
        title=resources.get("title", "相談窓口のご案内"),
        emergency_message=resources.get("emergency_message", ""),
    )
    return status.to_client_dict()


class CheckpointBuildError(RuntimeError):
    """Raised when deepcopy fails before mutation may start."""


def _build_checkpoint(session: Any) -> SessionCheckpoint:
    entries: dict[str, CheckpointEntry] = {}
    for k in _CHECKPOINT_KEYS:
        if k in session:
            try:
                entries[k] = CheckpointEntry(existed=True, value=copy.deepcopy(session.get(k)))
            except Exception as exc:
                raise CheckpointBuildError(f"deepcopy failed for key={k}") from exc
        else:
            entries[k] = CheckpointEntry(existed=False, value=None)
    modified_existed = hasattr(session, "modified")
    modified_value = getattr(session, "modified", None) if modified_existed else None
    if modified_existed:
        try:
            modified_value = copy.deepcopy(modified_value)
        except Exception as exc:
            raise CheckpointBuildError("deepcopy failed for modified") from exc
    return SessionCheckpoint(
        entries=entries,
        modified_existed=modified_existed,
        modified_value=modified_value,
    )


def _restore_checkpoint(session: Any, checkpoint: SessionCheckpoint) -> bool:
    try:
        for k, entry in checkpoint.entries.items():
            if entry.existed:
                session[k] = copy.deepcopy(entry.value)
            elif k in session:
                session.pop(k, None)
        if checkpoint.modified_existed and hasattr(session, "modified"):
            session.modified = copy.deepcopy(checkpoint.modified_value)
        if not checkpoint.deep_equals_session(session):
            logger.error("policy_d2 rollback equality check failed")
            return False
        return True
    except Exception:
        logger.exception("policy_d2 rollback failed")
        return False


def _try_db_save_status(sid: Optional[str], data: dict) -> str:
    """Return confirmed|failed|unknown|memory_only|skipped.

    Note: legacy save_session_to_db always returns True; we probe underlying
    db.save_session when available so db_commit_unknown can be honest.
    """
    if not sid:
        return "skipped"
    try:
        from src.services.session_manager import get_database, touch_session_in_memory

        db = get_database()
        if not db or not db.is_available():
            touch_session_in_memory(sid, data)
            return "memory_only"
        try:
            ok = db.save_session(sid, data)
        except Exception:
            logger.exception("policy_d2 db.save_session raised sid=%s", sid)
            touch_session_in_memory(sid, data)
            return "unknown"
        touch_session_in_memory(sid, data)
        if ok is True:
            return "confirmed"
        if ok is False:
            return "failed"
        return "unknown"
    except Exception:
        logger.exception("policy_d2 db save status probe failed")
        return "unknown"


def _apply_mutation_plan(
    session: Any,
    sid: Optional[str],
    plan: MutationPlan,
    *,
    client_info: Any = None,
) -> dict[str, Any]:
    """Apply declarative MutationPlan to in-memory session. Returns bot message dict."""
    from src.services.sage_bot_response import build_bot_response
    from src.services.session_manager import append_user_message
    from src.services.status_diagnosis_builder import build_notice_status

    if plan.append_user and plan.user_text:
        append_user_message(session, plan.user_text)

    sage = plan.sage_diagnosis
    if sage is None and plan.append_bot:
        sage = build_notice_status(
            plan.bot_legacy_content,
            title=plan.bot_title,
            variant=plan.bot_variant,
            kind=plan.bot_kind,
            show_feedback=True,
        ).to_client_dict()

    bot: dict[str, Any] = {}
    if plan.append_bot:
        bot = build_bot_response(
            session,
            sid,
            sage_diagnosis=sage,
            legacy_content=plan.bot_legacy_content,
            inappropriate_request=plan.record_inappropriate,
            request_type=plan.inappropriate_type or None,
            illegal_drug_block=plan.set_illegal_drug_block,
        )
        session.setdefault("messages", []).append(bot)

    if plan.record_inappropriate:
        session.setdefault("inappropriate_requests", []).append(
            {
                "type": plan.inappropriate_type,
                "timestamp": datetime.now().isoformat(),
                "blocked": plan.inappropriate_blocked,
                "source": "policy_enforcement_d2",
            }
        )

    if plan.set_illegal_drug_block:
        session["illegal_drug_block"] = True

    if plan.start_counseling:
        from src.services.counseling_response import start_counseling_mode

        start_counseling_mode(session, plan.counseling_symptom_type, [])

    if hasattr(session, "modified"):
        session.modified = True

    return bot


def _persist_after_mutation(
    session: Any,
    sid: Optional[str],
    client_info: Any,
) -> str:
    from src.services.session_manager import get_next_user_number

    if not sid:
        return "skipped"
    data = {
        "session_id": sid,
        "username": session.get("username", f"ユーザー{get_next_user_number()}"),
        "messages": list(session.get("messages", [])),
        "session_active": True,
        "last_activity": datetime.now(),
        "client_ip": getattr(client_info, "client_ip", "") if client_info else "",
        "user_agent": getattr(client_info, "user_agent", "") if client_info else "",
        "user_attributes": session.get("user_attributes", {}),
        "inappropriate_requests": list(session.get("inappropriate_requests", [])),
    }
    if session.get("illegal_drug_block"):
        data["illegal_drug_block"] = True
    if "counseling_mode" in session:
        data["counseling_mode"] = session.get("counseling_mode")
    return _try_db_save_status(sid, data)


def _receipt_lookup(session: Any, turn_id: str, kind: str) -> Optional[ResponseTuple]:
    """Request-local dedup only — not durable exactly-once."""
    receipt = None
    if session is not None:
        receipt = session.get(_REQUEST_LOCAL_DEDUP_KEY)
    if not isinstance(receipt, dict):
        return None
    if receipt.get("turn_id") != turn_id or receipt.get("policy_kind") != kind:
        return None
    body = receipt.get("body")
    status = receipt.get("status_code", 200)
    if isinstance(body, dict):
        return (body, int(status))
    return None


def _store_receipt(
    session: Any,
    turn_id: str,
    kind: str,
    body: dict,
    status_code: int,
) -> None:
    """Store request-local dedup token. Cleared on next turn by overwrite."""
    if session is None:
        return
    session[_REQUEST_LOCAL_DEDUP_KEY] = {
        "turn_id": turn_id,
        "policy_kind": kind,
        "body": body,
        "status_code": status_code,
        "stored_at": datetime.now().isoformat(),
        "scope": "request_local_dedup",
    }
    # Do not persist as durable claim
    session.pop("_policy_enforcement_d2_receipt", None)


def _terminal_from_adapter(
    session: Any,
    sid: Optional[str],
    decision: PolicyDecision,
    adapter: AdapterResult,
    *,
    client_info: Any,
    snapshot: TurnSignalSnapshot,
    user_text: str = "",
    triage_result: Optional[dict] = None,
) -> PolicyEnforcementResult:
    if not (adapter.content or "").strip():
        if decision.kind in _POLICY_BOUNDARY_KINDS:
            return _policy_boundary_fallback(
                session,
                decision,
                snapshot=snapshot,
                user_text=user_text,
                fallback_reason="empty_content",
                sid=sid,
                triage_result=triage_result,
                mutation_started=False,
            )
        return _safe_fallback(
            session,
            decision,
            fallback_reason="empty_content",
            no_mutation_claim=True,
            mutation_started=False,
            snapshot=snapshot,
        )

    prior = _receipt_lookup(session, snapshot.turn_id, str(decision.kind))
    if prior is not None:
        body, code = prior
        return PolicyEnforcementResult(
            handled=True,
            response=body,
            status_code=code,
            policy_kind=decision.kind,
            action=decision.action,
            fallback_reason=None,
            observability_fields={
                **snapshot.observability_fields(),
                "request_local_dedup_replay": True,
                **(adapter.observability or {}),
            },
            db_commit_status="skipped",
        )

    try:
        checkpoint = _build_checkpoint(session)
    except CheckpointBuildError:
        logger.exception("policy_d2 checkpoint build failed; mutation not started")
        if decision.kind in _POLICY_BOUNDARY_KINDS:
            return _policy_boundary_fallback(
                session,
                decision,
                snapshot=snapshot,
                user_text=user_text,
                fallback_reason="adapter_error",
                sid=sid,
                triage_result=triage_result,
                mutation_started=False,
            )
        return _safe_fallback(
            session,
            decision,
            fallback_reason="adapter_error",
            mutation_started=False,
            snapshot=snapshot,
        )

    mutation_started = True
    try:
        _apply_mutation_plan(
            session, sid, adapter.mutation_plan, client_info=client_info
        )
    except Exception:
        logger.exception("policy_d2 mutation apply failed")
        rolled = _restore_checkpoint(session, checkpoint)
        if decision.kind in _POLICY_BOUNDARY_KINDS:
            return _policy_boundary_fallback(
                session,
                decision,
                snapshot=snapshot,
                user_text=user_text,
                fallback_reason="adapter_error",
                sid=sid,
                triage_result=triage_result,
                mutation_started=True,
                rollback_ok=rolled,
            )
        return _safe_fallback(
            session,
            decision,
            fallback_reason="adapter_error",
            mutation_started=True,
            snapshot=snapshot,
            rollback_ok=rolled,
        )

    db_status = _persist_after_mutation(session, sid, client_info)

    if db_status in ("failed", "unknown"):
        rolled = _restore_checkpoint(session, checkpoint)
        # R10 M-FB-REASON: keep primary cause; recovery is separate.
        primary = (
            "db_commit_unknown" if db_status == "unknown" else "db_save_failed"
        )
        recovery = "rollback_ok" if rolled else "rollback_failed"
        if not rolled:
            logger.error("INTERNAL_ALERT policy_d2 rollback_failed sid=%s", sid)
        if decision.kind in _POLICY_BOUNDARY_KINDS:
            return _policy_boundary_fallback(
                session,
                decision,
                snapshot=snapshot,
                user_text=user_text,
                fallback_reason=primary,
                sid=sid,
                triage_result=triage_result,
                mutation_started=True,
                rollback_ok=rolled,
                db_commit_status=db_status,
            )
        return _safe_fallback(
            session,
            decision,
            fallback_reason=primary,
            mutation_started=True,
            snapshot=snapshot,
            rollback_ok=rolled,
            db_commit_status=db_status,
            recovery_status=recovery,
        )

    body: dict[str, Any] = {
        "status": "ok",
        "message_count": len(session.get("messages", [])),
    }
    code = 200
    _store_receipt(session, snapshot.turn_id, str(decision.kind), body, code)
    return PolicyEnforcementResult(
        handled=True,
        response=body,
        status_code=code,
        policy_kind=decision.kind,
        action=decision.action,
        fallback_reason=None,
        observability_fields={
            **snapshot.observability_fields(),
            **(adapter.observability or {}),
            "db_commit_status": db_status,
        },
        db_commit_status=db_status,
    )


def _safe_fallback(
    session: Any,
    decision: PolicyDecision | None,
    *,
    fallback_reason: str,
    mutation_started: bool,
    snapshot: TurnSignalSnapshot,
    rollback_ok: bool | None = None,
    db_commit_status: str | None = None,
    no_mutation_claim: bool = False,  # ignored — NM disabled (R7-E)
    recovery_status: str | None = None,
) -> PolicyEnforcementResult:
    del no_mutation_claim
    # R7-E: always SF-E1; never NM
    sage = build_sf_e1_response(no_mutation_claim=False)
    from src.services.sage_bot_response import build_bot_response

    if recovery_status is None and rollback_ok is not None:
        recovery_status = "rollback_ok" if rollback_ok else "rollback_failed"

    try:
        bot = build_bot_response(
            session,
            None,
            sage_diagnosis=sage,
            legacy_content=sage.get("message") or "",
        )
        if mutation_started and rollback_ok:
            pass  # restored; do not re-append
        elif not mutation_started:
            pass
        else:
            session.setdefault("messages", []).append(bot)
            if hasattr(session, "modified"):
                session.modified = True
    except Exception:
        logger.debug("sf-e1 bot build skipped", exc_info=True)

    body = {
        "status": "error",
        "error": "policy_enforcement_fallback",
        "fallback_reason": fallback_reason,
        "fallback_reason_primary": fallback_reason,
        "recovery_status": recovery_status,
        "db_commit_status": db_commit_status,
        "rollback_ok": rollback_ok,
        "sage_diagnosis": sage,
        "message_count": len(session.get("messages", [])) if session is not None else 0,
    }
    logger.error(
        "policy_d2 safe_fallback reason=%s recovery=%s nm_disabled=1 kind=%s turn=%s rollback_ok=%s",
        fallback_reason,
        recovery_status,
        getattr(decision, "kind", None),
        snapshot.turn_id,
        rollback_ok,
    )
    return PolicyEnforcementResult(
        handled=True,
        response=body,
        status_code=200,
        policy_kind=getattr(decision, "kind", None),
        action=getattr(decision, "action", None),
        fallback_reason=fallback_reason,
        observability_fields={
            **snapshot.observability_fields(),
            "safe_fallback": "SF-E1",
            "sf_e1_nm_enabled": False,
            "db_commit_status": db_commit_status,
            "rollback_ok": rollback_ok,
            "fallback_reason_primary": fallback_reason,
            "recovery_status": recovery_status,
        },
        db_commit_status=db_commit_status,
    )


_POLICY_BOUNDARY_KINDS = frozenset(
    {
        "prescription",
        "controlled_or_illegal",
        "medical_examination",
        "ambiguous_controlled",
    }
)


def _policy_boundary_fallback(
    session: Any,
    decision: PolicyDecision,
    *,
    snapshot: TurnSignalSnapshot,
    user_text: str,
    fallback_reason: str,
    sid: Optional[str] = None,
    triage_result: Optional[dict] = None,
    mutation_started: bool = False,
    rollback_ok: bool | None = None,
    db_commit_status: str | None = None,
) -> PolicyEnforcementResult:
    """F-H03-R2: known policy cue → boundary UX even when adapter/DB fails.

    Prefer typed boundary content over generic SF-E1. Does not claim durable
    mutation / DB success. Never weakens crisis deferral.
    """
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    content = ""
    title = "ご案内"
    kind = f"policy_{decision.kind or 'boundary'}_fallback"
    try:
        adapter = run_policy_adapter(
            decision,
            snapshot,
            user_text=user_text,
            triage_result=triage_result,
        )
        if adapter is not None and (adapter.content or "").strip():
            content = adapter.content.strip()
            if adapter.mutation_plan and adapter.mutation_plan.bot_title:
                title = adapter.mutation_plan.bot_title
            if adapter.mutation_plan and adapter.mutation_plan.bot_kind:
                kind = adapter.mutation_plan.bot_kind
    except Exception:
        logger.exception("policy_d2 boundary_fallback adapter re-entry failed")

    if not content:
        # Static last-resort copy — still boundary, never SF-E1 system_error.
        if decision.kind == "prescription":
            content = (
                "申し訳ありません。当サービスでは医師の処方箋が必要な医薬品の処方や"
                "処方の代行はできません。必要に応じて医療機関を受診してください。"
            )
            title = "処方について"
        elif decision.kind == "controlled_or_illegal":
            content = (
                "ご相談の内容にはお応えできません。"
                "違法・規制薬物に関する入手や使用の案内はできません。"
            )
            title = "ご案内"
        elif decision.kind == "medical_examination":
            content = (
                "当サービスでは診断や病名の確定はできません。"
                "症状が続く場合は医療機関を受診してください。"
            )
            title = "診察について"
        else:
            content = (
                "睡眠薬・規制の可能性があるお薬については、処方の代行や入手案内はできません。"
                "市販の一般的な情報であれば、症状などをお書きください。"
            )
            title = "ご案内"

    sage = build_notice_status(
        content,
        title=title,
        variant="notice",
        kind=kind,
        show_feedback=True,
    ).to_client_dict()

    recovery_status = None
    if rollback_ok is not None:
        recovery_status = "rollback_ok" if rollback_ok else "rollback_failed"

    # R7 rollback invariant: after successful checkpoint restore, do NOT
    # re-dirty the session. Boundary UX is returned in the HTTP body only.
    # Pre-mutation adapter failures may append a boundary bot message.
    session_append = not (mutation_started and rollback_ok is True)
    try:
        bot = build_bot_response(
            session,
            sid,
            sage_diagnosis=sage,
            legacy_content=content,
            inappropriate_request=True,
            request_type=str(decision.kind or "policy"),
        )
        if session is not None and session_append:
            session.setdefault("messages", []).append(bot)
            if hasattr(session, "modified"):
                session.modified = True
    except Exception:
        logger.exception("policy_d2 boundary_fallback bot build failed")

    body = {
        "status": "ok",
        "policy_boundary_fallback": True,
        "fallback_reason": fallback_reason,
        "fallback_reason_primary": fallback_reason,
        "recovery_status": recovery_status,
        "db_commit_status": db_commit_status or "skipped",
        "rollback_ok": rollback_ok,
        "sage_diagnosis": sage,
        "message_count": len(session.get("messages", [])) if session is not None else 0,
        "recommend_stopped": True,
        "session_ops_mutated": False,
        "session_boundary_appended": bool(session_append),
    }
    logger.warning(
        "policy_d2 boundary_fallback reason=%s kind=%s turn=%s",
        fallback_reason,
        decision.kind,
        snapshot.turn_id,
    )
    return PolicyEnforcementResult(
        handled=True,
        response=body,
        status_code=200,
        policy_kind=decision.kind,
        action=decision.action,
        fallback_reason=fallback_reason,
        observability_fields={
            **snapshot.observability_fields(),
            "safe_fallback": "policy_boundary",
            "disposition": "policy_boundary_fallback",
            "fallback_reason_primary": fallback_reason,
            "recovery_status": recovery_status,
            "db_commit_status": db_commit_status or "skipped",
            "rollback_ok": rollback_ok,
            "recommend_stopped": True,
            "session_ops_mutated": False,
        },
        db_commit_status=db_commit_status or "skipped",
    )


def _crisis_resources_terminal(
    session: Any,
    decision: PolicyDecision | None,
    *,
    snapshot: TurnSignalSnapshot,
    sid: Optional[str] = None,
) -> PolicyEnforcementResult:
    """H-04: crisis/emergency + detector_error → crisis resources UX (not SF-E1).

    Terminal: stops recommend / SessionOps / Jev continuation. Does not apply
    SessionOps MutationPlan. Appends crisis bot message only.
    """
    from src.services.sage_bot_response import build_bot_response

    language = "ja"
    try:
        if session is not None:
            language = str(session.get("language") or "ja")
    except Exception:
        language = "ja"

    sage = build_crisis_resources_response(language=language)
    legacy = sage.get("message") or ""
    try:
        bot = build_bot_response(
            session,
            sid,
            sage_diagnosis=sage,
            legacy_content=legacy,
            crisis_support=True,
        )
        if session is not None:
            session.setdefault("messages", []).append(bot)
            session["crisis_detected"] = True
            if hasattr(session, "modified"):
                session.modified = True
    except Exception:
        logger.exception("crisis_resources bot build failed; returning sage only")

    body = {
        "status": "ok",
        "crisis_support": True,
        "fallback_reason": "defer_to_crisis_safety",
        "fallback_reason_primary": "defer_to_crisis_safety",
        "sage_diagnosis": sage,
        "message_count": len(session.get("messages", [])) if session is not None else 0,
        # Gate B contract markers — no recommend / no SessionOps mutation claim
        "recommend_stopped": True,
        "session_ops_mutated": False,
    }
    logger.warning(
        "policy_d2 crisis_resources_terminal turn=%s errors=%s",
        snapshot.turn_id,
        list(snapshot.signals.detector_errors),
    )
    return PolicyEnforcementResult(
        handled=True,
        response=body,
        status_code=200,
        policy_kind=getattr(decision, "kind", None),
        action=getattr(decision, "action", None),
        fallback_reason="defer_to_crisis_safety",
        observability_fields={
            **snapshot.observability_fields(),
            "safe_fallback": "crisis_resources",
            "disposition": "crisis_resources",
            "fallback_reason_primary": "defer_to_crisis_safety",
            "recommend_stopped": True,
            "session_ops_mutated": False,
        },
        db_commit_status="skipped",
    )


def enforce_policy_decision(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    session: Any,
    sid: Optional[str],
    user_text: str,
    client_info: Any = None,
    triage_result: Optional[dict] = None,
) -> PolicyEnforcementResult:
    """Enforce typed PolicyDecision. Returns handled=False to continue routing."""
    # R19 H-04: explicit crisis deferral from resolve — never SF-E1.
    if decision.reason_code == "defer_to_crisis_safety":
        return _crisis_resources_terminal(
            session, decision, snapshot=snapshot, sid=sid
        )

    if decision.action == "continue" or decision.kind is None:
        if decision.reason_code == "incomplete_evaluation":
            # Belt-and-suspenders: crisis/emergency cues OR crisis detector
            # failure OR soft SI paraphrase win over SF-E1 (H-04 / F-H04-R1).
            sig = snapshot.signals
            errors = getattr(sig, "detector_errors", ()) or ()
            detector_view = (
                getattr(snapshot, "detector_text", None)
                or getattr(snapshot, "normalized_text", None)
                or user_text
                or ""
            )
            soft_si = False
            try:
                from src.dialogue.routing.pre_route_signals import (
                    _soft_si_paraphrase_cues,
                )

                soft_si = _soft_si_paraphrase_cues(detector_view)
            except Exception:
                soft_si = False
            if (
                getattr(sig, "crisis_detected", False)
                or getattr(sig, "emergency_detected", False)
                or "crisis_detector_error" in errors
                or soft_si
            ):
                return _crisis_resources_terminal(
                    session, decision, snapshot=snapshot, sid=sid
                )
            return _safe_fallback(
                session,
                decision,
                fallback_reason="incomplete_evaluation",
                no_mutation_claim=True,
                mutation_started=False,
                snapshot=snapshot,
            )
        return PolicyEnforcementResult(
            handled=False,
            response=None,
            status_code=None,
            policy_kind=None,
            action="continue",
            fallback_reason=None,
            observability_fields=snapshot.observability_fields(),
        )

    if decision.kind not in _POLICY_BOUNDARY_KINDS:
        return _safe_fallback(
            session,
            decision,
            fallback_reason="unknown_kind",
            mutation_started=False,
            snapshot=snapshot,
        )

    try:
        adapter = run_policy_adapter(
            decision,
            snapshot,
            user_text=user_text,
            triage_result=triage_result,
        )
    except Exception:
        logger.exception("policy_d2 adapter exception")
        # F-H03-R2: known cue → boundary UX, not SF-E1.
        return _policy_boundary_fallback(
            session,
            decision,
            snapshot=snapshot,
            user_text=user_text,
            fallback_reason="adapter_error",
            sid=sid,
            triage_result=triage_result,
            mutation_started=False,
        )

    if adapter is None:
        return PolicyEnforcementResult(
            handled=False,
            response=None,
            status_code=None,
            policy_kind=decision.kind,
            action="continue",
            fallback_reason=None,
            observability_fields=snapshot.observability_fields(),
        )

    return _terminal_from_adapter(
        session,
        sid,
        decision,
        adapter,
        client_info=client_info,
        snapshot=snapshot,
        user_text=user_text,
        triage_result=triage_result,
    )


def resolve_and_enforce(
    snapshot: TurnSignalSnapshot,
    *,
    session: Any,
    sid: Optional[str],
    user_text: str,
    client_info: Any = None,
    triage_bag: Mapping[str, Any] | None = None,
    triage_result: Optional[dict] = None,
) -> tuple[TurnSignalSnapshot, PolicyDecision, PolicyEnforcementResult]:
    """Merge triage → resolve → enforce. Single entry for pipeline."""
    merged = snapshot.with_additive(triage_bag) if triage_bag else snapshot
    decision = resolve_policy_decision(merged)
    result = enforce_policy_decision(
        decision,
        merged,
        session=session,
        sid=sid,
        user_text=user_text,
        client_info=client_info,
        triage_result=triage_result,
    )
    return merged, decision, result
