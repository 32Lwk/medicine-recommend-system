"""AgentDispatcher — IntentRouter 決定に基づく dispatch（Wave 1b 本線、フラグ付き）。"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from config.llm_flags import is_intent_router_dispatch_enabled
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)

ResponseTuple = tuple[dict, int]

_SESSION_SUB_ALIASES: dict[str, str] = {
    "delete_confirm": "delete",
    "status_card": "status",
    "pending_clear": "pending_clear",
    "cancel": "pending_clear",
}

_PRIMARY_TO_TRIAGE_CATEGORY: dict[str, str] = {
    "Physical": "Physical",
    "Emergency": "Emergency",
    "Counseling": "Emotional",
    "Concierge": "Other",
    "Store": "Other",
    "SessionOps": "Other",
    "Security": "Other",
}

_ROUTE_HANDLERS: dict[str, str] = {
    "Physical": "physical_agent",
    "SessionOps": "session_ops",
    "Concierge": "concierge_agent",
    "Emergency": "emergency_agent",
    "Security": "security_gate",
    "Store": "store_inquiry",
    "Counseling": "counseling_processor",
    "Unknown": "legacy_fallback",
}


def resolve_handler_name(decision: RouteDecision) -> str:
    return _ROUTE_HANDLERS.get(decision.primary_route, "legacy_fallback")


def _decision_from_session(session: Any) -> RouteDecision | None:
    raw = session.get("_intent_router_shadow") if session is not None else None
    if not isinstance(raw, dict) or not raw.get("primary_route"):
        return None
    return RouteDecision(
        primary_route=raw["primary_route"],  # type: ignore[arg-type]
        sub_route=raw.get("sub_route"),
        confidence=float(raw.get("confidence") or 0.0),
        resolved_by=raw.get("resolved_by") or "legacy",  # type: ignore[arg-type]
        source=str(raw.get("source") or ""),
    )


def _load_decision(ctx: Any) -> RouteDecision | None:
    decision = _decision_from_session(ctx.session)
    if decision is not None:
        return decision

    from src.dialogue.routing.router import resolve_route

    return resolve_route(
        ctx.sanitized_message or ctx.user_message,
        ctx.session,
        ctx.sid,
        triage_result=ctx.triage_result,
        client=ctx.recommendation_client,
    )


def _apply_decision_to_context(ctx: Any, decision: RouteDecision) -> None:
    triage = dict(ctx.triage_result or {})
    primary = decision.primary_route
    triage["category"] = _PRIMARY_TO_TRIAGE_CATEGORY.get(
        primary, str(triage.get("category") or "Other")
    )
    triage["_intent_router_dispatch"] = True

    sub = decision.sub_route or ""
    if primary == "Concierge" and sub:
        triage["concierge_intent"] = sub
    elif primary == "SessionOps" and sub:
        triage["concierge_intent"] = "session_ops"
        triage["session_intent"] = _SESSION_SUB_ALIASES.get(sub, sub)
    elif primary == "Store":
        triage["subcategory"] = "store_inquiry"
        if sub:
            triage["_store_dispatch_sub"] = sub
    elif primary == "Physical":
        if sub == "fever_flow":
            triage["subcategory"] = "fever"
        elif sub in ("medicine_followup_qa", "medicine_side_effect_qa", "symptom_prompt_sports"):
            triage["subcategory"] = sub
        elif sub and sub != "rule_based_recommend":
            triage["subcategory"] = sub
    elif primary == "Emergency" and sub:
        triage["subcategory"] = sub

    ctx.triage_result = triage
    ctx.session["last_triage_result"] = triage


def _should_skip_dispatch(decision: RouteDecision) -> bool:
    if decision.primary_route == "Unknown":
        return True
    if decision.sub_route == "clarification":
        return True
    return False


def _log_dispatch(ctx: Any, decision: RouteDecision, *, handled: bool) -> None:
    dialogue_flags: dict[str, bool] | None = None
    layer_used = None
    execution_lock = None
    if isinstance(decision.meta, dict):
        layer_used = decision.meta.get("layer_used")
    routing_raw = (ctx.session or {}).get("_routing_decision") if ctx.session else None
    if isinstance(routing_raw, dict):
        layer_used = layer_used or routing_raw.get("layer_used")
        execution_lock = routing_raw.get("execution_lock")
    try:
        from src.dialogue.context import load_dialogue_context

        flags = load_dialogue_context(ctx.session).get("flags") or {}
        picked = {
            key: True
            for key in ("fever_context", "pending_cancelled_by_physical")
            if flags.get(key)
        }
        dialogue_flags = picked or None
    except Exception:
        pass
    try:
        from src.utils.structured_logger import (
            emit_dialogue_route_dispatch,
            emit_dialogue_route_execution,
        )

        emit_dialogue_route_dispatch(
            session_id=ctx.sid or "",
            user_input=ctx.sanitized_message or ctx.user_message or "",
            decision=decision.to_dialogue_routing_dict(),
            handler=resolve_handler_name(decision),
            handled=handled,
            dialogue_flags=dialogue_flags,
        )
        resolved_exec = None
        if ctx.triage_result:
            resolved_exec = ctx.triage_result.get("concierge_intent")
        emit_dialogue_route_execution(
            session_id=ctx.sid or "",
            user_input=ctx.sanitized_message or ctx.user_message or "",
            dispatch_sub_route=decision.sub_route,
            resolved_concierge_intent=resolved_exec,
            resolved_execution_intent=resolved_exec,
            layer_used=layer_used,
            mismatch=False,
            handler=resolve_handler_name(decision),
            extra={"execution_lock": execution_lock, "handled": handled},
        )
    except Exception:
        logger.debug("emit_dialogue_route_dispatch skipped", exc_info=True)


def _dispatch_physical(ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
    from src.services.medicine_context_routing import resolve_medicine_context_route

    sub = (ctx.session.get("_intent_router_dispatch") or {}).get("sub_route")
    if not sub and ctx.triage_result:
        sub = ctx.triage_result.get("subcategory")
    user_msg = ctx.sanitized_message or ctx.user_message

    try:
        from config.llm_flags import is_medicine_side_effect_qa_enabled
        from src.services.medicine_side_effect_routing import is_medicine_side_effect_route

        side_effect_ok = is_medicine_side_effect_qa_enabled(ctx.sid) and (
            sub == "medicine_side_effect_qa" or is_medicine_side_effect_route(user_msg)
        )
        if side_effect_ok:
            from src.handlers.chat.medicine_side_effect_handlers import (
                handle_medicine_side_effect_qa,
            )

            return handle_medicine_side_effect_qa(
                ctx.session,
                ctx.client_info,
                ctx.sid,
                ctx.original_user_message or user_msg,
            )
    except ImportError:
        pass

    ctx_route = resolve_medicine_context_route(
        ctx.session,
        ctx.sid,
        user_msg,
        client=ctx.recommendation_client,
        triage_result=ctx.triage_result,
    )
    effective_sub = sub or ""
    from src.services.medicine_discovery_routing import session_has_recommended_medicines

    followup_ok = ctx_route == "followup_qa" or (
        effective_sub in ("medicine_followup_qa",)
        and session_has_recommended_medicines(ctx.session, ctx.sid)
    )
    if followup_ok:
        from src.handlers.chat.medicine_context_handlers import handle_medicine_followup_qa

        return handle_medicine_followup_qa(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.original_user_message or ctx.user_message,
        )
    if effective_sub in ("symptom_prompt_sports",) or ctx_route == "symptom_prompt":
        from src.handlers.chat.medicine_context_handlers import handle_sports_symptom_prompt

        return handle_sports_symptom_prompt(
            ctx.session,
            ctx.sid,
            ctx.original_user_message or ctx.user_message,
        )
    if ctx_route == "cold_symptom_chip_prompt":
        from src.handlers.chat.medicine_context_handlers import handle_cold_symptom_chip_prompt

        return handle_cold_symptom_chip_prompt(
            ctx.session,
            ctx.sid,
            ctx.original_user_message or ctx.user_message,
        )

    from src.handlers.chat.chat_symptom_route import run_symptom_recommendation
    from src.services.llm_metrics import merge_into_user_info

    return run_symptom_recommendation(
        ctx.session,
        ctx.client_info,
        ctx.sid,
        monitor,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.processed_message or ctx.sanitized_message,
        ctx.triage_result,
        ctx.recommendation_client,
        user_agent=ctx.user_agent,
        client_ip=ctx.client_ip,
        merge_into_user_info=merge_into_user_info,
    )


def _dispatch_emergency(ctx: Any) -> Optional[ResponseTuple]:
    from src.handlers.chat.emergency_dispatch import dispatch_emergency

    mod_label = None
    if ctx.triage_result:
        mod_label = ctx.triage_result.get("_moderation_label")
    return dispatch_emergency(
        ctx.session,
        ctx.client_info,
        ctx.sid,
        ctx.sanitized_message,
        ctx.recommendation_client,
        ctx.triage_result,
        moderation_label=mod_label,
        trace_id=getattr(ctx, "trace_id", None),
    )


def _dispatch_store(ctx: Any) -> Optional[ResponseTuple]:
    if ctx.inappropriate_request_detected:
        return None
    from src.agents.store_inquiry_agent import handle_store_inquiry

    return handle_store_inquiry(
        ctx.session,
        ctx.client_info,
        ctx.sid,
        ctx.sanitized_message,
        ctx.recommendation_client,
        ctx.triage_result,
        display_user_message=ctx.original_user_message or ctx.user_message,
    )


def _dispatch_concierge(ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
    from src.handlers.chat.chat_concierge_route import try_concierge_response

    return try_concierge_response(
        ctx.session,
        ctx.client_info,
        ctx.sid,
        ctx.original_user_message or ctx.user_message,
        ctx.sanitized_message,
        ctx.triage_result,
        ctx.recommendation_client,
        monitor=monitor,
        processed_message=ctx.processed_message or ctx.sanitized_message,
        routing_ctx=getattr(ctx, "routing", None),
    )


def _dispatch_counseling(ctx: Any) -> Optional[ResponseTuple]:
    from src.agents.counseling_manager import start_counseling
    from src.handlers.chat.chat_emotional_route import (
        detect_insomnia_keyword,
        detect_sleepiness_keyword,
    )

    resp, _ = start_counseling(
        ctx.session,
        ctx.sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.triage_result,
        ctx.recommendation_client,
        has_sleepiness_keyword=ctx.session.get("has_sleepiness_keyword")
        or detect_sleepiness_keyword(ctx.sanitized_message),
        has_insomnia_keyword=detect_insomnia_keyword(ctx.sanitized_message),
    )
    return resp


def _dispatch_session_ops(ctx: Any) -> Optional[ResponseTuple]:
    from src.dialogue.session_ops import try_handle_session_ops

    return try_handle_session_ops(
        ctx.session,
        ctx.sid,
        ctx.sanitized_message or ctx.user_message,
        ctx.recommendation_client,
        triage_result=ctx.triage_result,
    )


def _dispatch_security(ctx: Any) -> Optional[ResponseTuple]:
    from src.handlers.chat.chat_inappropriate_route import (
        handle_inappropriate_message_if_detected,
    )

    return handle_inappropriate_message_if_detected(
        ctx.session,
        ctx.client_info,
        ctx.sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.recommendation_client,
    )


_DISPATCH_TABLE: dict[str, Callable[[Any, Any], Optional[ResponseTuple]]] = {
    "Physical": lambda ctx, monitor: _dispatch_physical(ctx, monitor),
    "Emergency": lambda ctx, _monitor: _dispatch_emergency(ctx),
    "Store": lambda ctx, _monitor: _dispatch_store(ctx),
    "Concierge": lambda ctx, monitor: _dispatch_concierge(ctx, monitor),
    "Counseling": lambda ctx, _monitor: _dispatch_counseling(ctx),
    "SessionOps": lambda ctx, _monitor: _dispatch_session_ops(ctx),
    "Security": lambda ctx, _monitor: _dispatch_security(ctx),
}


def try_agent_dispatch(ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
    """
    IntentRouter 決定に従い legacy handler へ dispatch。
    未対応・clarification は None（ChatOrchestrator へフォールバック）。
    """
    if not is_intent_router_dispatch_enabled(ctx.sid):
        return None

    decision = _load_decision(ctx)
    if decision is None or _should_skip_dispatch(decision):
        return None

    _apply_decision_to_context(ctx, decision)
    ctx.session["_intent_router_dispatch"] = {
        **decision.to_dialogue_routing_dict(),
        "handler": resolve_handler_name(decision),
    }
    ctx.session["_router_dispatch_attempted"] = True

    dispatch_fn = _DISPATCH_TABLE.get(decision.primary_route)
    if dispatch_fn is None:
        _log_dispatch(ctx, decision, handled=False)
        return None

    t0 = time.time()
    try:
        resp = dispatch_fn(ctx, monitor)
    except Exception:
        logger.exception(
            "AgentDispatcher failed route=%s sid=%s",
            decision.primary_route,
            ctx.sid,
        )
        _log_dispatch(ctx, decision, handled=False)
        return None

    logger.info(
        "AgentDispatcher route=%s/%s sid=%s handled=%s resolved_by=%s ms=%.0f",
        decision.primary_route,
        decision.sub_route,
        ctx.sid,
        resp is not None,
        decision.resolved_by,
        (time.time() - t0) * 1000,
    )
    if resp is not None:
        ctx.session["_router_dispatch_handled_turn"] = True
        try:
            from src.dialogue.context import load_dialogue_context, save_dialogue_context

            dctx = load_dialogue_context(ctx.session)
            dctx["routing"] = {
                **decision.to_dialogue_routing_dict(),
                "handler": resolve_handler_name(decision),
                "dispatched": True,
            }
            save_dialogue_context(ctx.session, dctx, dual_write=False)
        except Exception:
            logger.debug("dialogue_state routing persist skipped", exc_info=True)
        ctx.session.pop("triage_clarify_sent", None)
        try:
            from src.dialogue.sync_legacy import sync_dialogue_legacy_mirrors

            sync_dialogue_legacy_mirrors(ctx.session, ctx.sid)
        except Exception:
            logger.debug("sync_dialogue_legacy_mirrors after dispatch skipped", exc_info=True)
        if decision.primary_route == "Physical":
            try:
                from src.dialogue.sync_legacy import clear_pending_medical_cancel_flag

                clear_pending_medical_cancel_flag(ctx.session, ctx.sid)
            except Exception:
                logger.debug("clear_pending_medical_cancel_flag skipped", exc_info=True)
    _log_dispatch(ctx, decision, handled=resp is not None)
    return resp
