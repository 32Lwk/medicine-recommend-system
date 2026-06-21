"""
ChatOrchestrator — トリアージ後の9エージェント経路を一点に集約
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from config.llm_flags import is_agent_enabled
from src.agents.protocols import HandoffResult
from src.agents.triage_agent import resolve_handoff
from src.handlers.orchestrator_route_result import OrchestratorRouteResult, RouteReason
from src.utils.agent_trace import log_agent_step

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_AGENT_STEP_MAP = {
    "Physical": "medicine_select",
    "Emotional": "counseling",
    "Ask": "symptom_analysis",
    "Other": "store",
    "Emergency": "emergency",
}

_ORCH_FALLBACK_MSG = (
    "一時的に自動処理を完了できませんでした。お手数ですが、もう一度お試しください。"
)


class ChatOrchestrator:
    def __init__(self, client: OpenAI, *, trace_id: Optional[str] = None):
        self._client = client
        self._trace_id = trace_id

    def route(
        self,
        ctx: Any,
        monitor: Any,
    ) -> OrchestratorRouteResult:
        triage = ctx.triage_result
        if not triage:
            return OrchestratorRouteResult(resolved=False, reason=RouteReason.NO_TRIAGE)

        sid = ctx.sid
        session = ctx.session
        handoff = resolve_handoff(
            triage,
            ctx.sanitized_message,
            session.get("user_attributes"),
        )
        session["agent_handoff"] = handoff.target
        session["agent_handoff_payload"] = handoff.payload
        if hasattr(session, "modified"):
            session.modified = True

        log_agent_step(
            self._trace_id,
            "ChatOrchestrator",
            "handoff",
            sid=sid,
            payload={"target": handoff.target, "category": triage.get("category")},
        )

        self._mark_step(sid, triage.get("category", "Other"))

        from src.services.concierge_intent import classify_concierge_intent
        from src.handlers.chat.chat_physical_route import apply_physical_category_overrides
        from src.services.confidence_policy import should_defer_category_routing
        from src.utils.input_helpers import reroute_symptom_general_other_to_physical

        social_text = (ctx.sanitized_message or ctx.user_message or "").strip()
        counseling_mode = session.get("counseling_mode") or {}
        social_intent = None
        if not counseling_mode.get("active"):
            social_intent = classify_concierge_intent(social_text)
        if social_intent in ("greeting", "thanks") and triage.get("category") != "Emergency":
            concierge_resp = self._route_concierge(ctx, monitor)
            if concierge_resp is not None:
                return OrchestratorRouteResult(
                    resolved=True,
                    response=concierge_resp,
                    reason=RouteReason.RESOLVED,
                    category=triage.get("category", "Other"),
                    subtype=f"concierge_{social_intent}",
                )

        user_text = ctx.sanitized_message or ctx.user_message or ""
        if self._needs_emergency_route(triage, handoff, user_text):
            resp = self._route_emergency(ctx)
            if resp:
                return OrchestratorRouteResult(
                    resolved=True,
                    response=resp,
                    reason=RouteReason.EMERGENCY,
                    category="Emergency",
                    subtype=session.get("emergency_subtype"),
                )
            return OrchestratorRouteResult(
                resolved=False,
                reason=RouteReason.EMERGENCY,
                category="Emergency",
            )

        drug_block = self._route_inappropriate_drug_block(ctx)
        if drug_block is not None:
            return OrchestratorRouteResult(
                resolved=True,
                response=drug_block,
                reason=RouteReason.RESOLVED,
                category=triage.get("category", "Other"),
                subtype="inappropriate_drug_block",
            )

        unrecognized = self._route_unrecognized_symptom(ctx)
        if unrecognized is not None:
            return OrchestratorRouteResult(
                resolved=True,
                response=unrecognized,
                reason=RouteReason.RESOLVED,
                category=triage.get("category", "Other"),
                subtype="unrecognized_symptom_input",
            )

        ambiguous_heart = self._route_ambiguous_heart(ctx)
        if ambiguous_heart is not None:
            return OrchestratorRouteResult(
                resolved=True,
                response=ambiguous_heart,
                reason=RouteReason.RESOLVED,
                category=triage.get("category", "Other"),
                subtype="ambiguous_heart_clarification",
            )

        from src.utils.input_helpers import should_prioritize_medical_route_over_store
        from src.services.store_inquiry_handler import is_probable_store_inquiry_any

        store_texts = (
            ctx.original_user_message,
            ctx.sanitized_message,
            ctx.user_message,
        )
        store_message = ctx.sanitized_message or ctx.user_message or ""
        skip_store_gate = should_prioritize_medical_route_over_store(
            ctx.triage_result,
            store_message,
        )
        if not skip_store_gate and is_probable_store_inquiry_any(
            *store_texts,
            triage_result=ctx.triage_result,
        ):
            resp = self._route_store(ctx)
            if resp is not None:
                return OrchestratorRouteResult(
                    resolved=True,
                    response=resp,
                    reason=RouteReason.RESOLVED,
                    category=triage.get("category", "Other"),
                )

        category = triage.get("category", "Other")
        confidence = float(triage.get("confidence") or 1.0)
        sanitized = ctx.sanitized_message or ctx.user_message or ""

        category, triage = reroute_symptom_general_other_to_physical(triage, sanitized)
        if category != ctx.triage_result.get("category"):
            ctx.triage_result = triage
            session["last_triage_result"] = triage
            if hasattr(session, "modified"):
                session.modified = True

        category = apply_physical_category_overrides(category, sanitized)
        if category != triage.get("category"):
            triage = {**triage, "category": category}
            ctx.triage_result = triage
            session["last_triage_result"] = triage
            if hasattr(session, "modified"):
                session.modified = True

        try:
            if should_defer_category_routing(category, confidence, session):
                return OrchestratorRouteResult(
                    resolved=False,
                    reason=RouteReason.UNHANDLED_CATEGORY,
                    category=category,
                )
            if category == "Emotional":
                resp = self._route_emotional(ctx)
            elif category == "Physical":
                resp = self._route_physical(ctx, monitor)
            elif category == "Ask":
                resp = self._route_ask(ctx)
            elif category == "Other":
                store_probable = (
                    not skip_store_gate
                    and is_probable_store_inquiry_any(
                        *store_texts,
                        triage_result=ctx.triage_result,
                    )
                )
                resp = None
                if not store_probable:
                    self._enrich_concierge_intent(ctx)
                    resp = self._route_concierge(ctx, monitor)
                if resp is None:
                    resp = self._route_store(ctx)
            else:
                resp = None

            if resp is not None:
                return OrchestratorRouteResult(
                    resolved=True,
                    response=resp,
                    reason=RouteReason.RESOLVED,
                    category=category,
                )
        except Exception as exc:
            logger.exception("ChatOrchestrator route failed: %s", exc)
            session.setdefault("messages", []).append({
                "type": "bot",
                "content": _ORCH_FALLBACK_MSG,
                "orchestrator_fallback": True,
                "timestamp": time.time(),
            })
            if hasattr(session, "modified"):
                session.modified = True
            return OrchestratorRouteResult(
                resolved=True,
                response=({"status": "ok", "message_count": len(session.get("messages", []))}, 200),
                reason=RouteReason.EXCEPTION_FALLBACK,
                category=category,
                meta={"error": str(exc)},
            )

        return OrchestratorRouteResult(
            resolved=False,
            reason=RouteReason.UNHANDLED_CATEGORY,
            category=category,
        )

    def _needs_emergency_route(
        self,
        triage: Dict[str, Any],
        handoff: HandoffResult,
        user_text: str = "",
    ) -> bool:
        sub = (triage.get("subcategory") or "").lower()
        if "ambiguous_heart" in sub:
            return False
        if (
            handoff.stop
            or triage.get("category") == "Emergency"
            or triage.get("requires_immediate_action")
        ):
            return True
        from src.agents.emergency_classifier import is_emergency_candidate

        return is_emergency_candidate(user_text, triage_result=triage)

    def _mark_step(self, sid: Optional[str], category: str) -> None:
        try:
            from src.services.processing_flows import flow_for_triage_category
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(sid, flow_for_triage_category(category))
            step = _AGENT_STEP_MAP.get(category, "triage")
            mark_processing_step(sid, step)
        except Exception as e:
            logger.debug("mark_processing_step skipped: %s", e)

    def _route_unrecognized_symptom(self, ctx: Any) -> Optional[ResponseTuple]:
        """Physical/Ask または低確信 Other の短い不明入力へ caution カードを返す。"""
        handoff = resolve_handoff(
            ctx.triage_result,
            ctx.sanitized_message,
            ctx.session.get("user_attributes"),
        )
        user_text = ctx.sanitized_message or ctx.user_message or ""
        if self._needs_emergency_route(ctx.triage_result, handoff, user_text):
            return None

        from src.utils.input_helpers import should_apply_unrecognized_symptom_gate

        if not should_apply_unrecognized_symptom_gate(
            ctx.triage_result,
            ctx.sanitized_message or ctx.user_message,
        ):
            return None

        from src.handlers.chat.chat_symptom_route import try_unrecognized_symptom_response

        t0 = time.time()
        resp = try_unrecognized_symptom_response(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.sanitized_message,
            ctx.user_message,
        )
        if resp is None:
            return None
        log_agent_step(
            self._trace_id,
            "ChatOrchestrator",
            "unrecognized_symptom",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
        )
        return resp

    def _route_ambiguous_heart(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.chat_ambiguous_heart_route import try_ambiguous_heart_clarification

        t0 = time.time()
        resp = try_ambiguous_heart_clarification(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.sanitized_message,
            ctx.user_message,
            ctx.triage_result or {},
        )
        if resp is None:
            return None
        log_agent_step(
            self._trace_id,
            "ChatOrchestrator",
            "ambiguous_heart",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
        )
        return resp

    def _route_emotional(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.agents.counseling_manager import start_counseling
        from src.handlers.chat.chat_emotional_route import (
            detect_insomnia_keyword,
            detect_sleepiness_keyword,
        )

        t0 = time.time()
        resp, _ = start_counseling(
            ctx.session,
            ctx.sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            self._client,
            has_sleepiness_keyword=ctx.session.get("has_sleepiness_keyword")
            or detect_sleepiness_keyword(ctx.sanitized_message),
            has_insomnia_keyword=detect_insomnia_keyword(ctx.sanitized_message),
        )
        log_agent_step(
            self._trace_id,
            "CounselingManager",
            "complete",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
        )
        return resp

    def _route_physical(self, ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.chat_symptom_route import run_symptom_recommendation
        from src.services.llm_metrics import merge_into_user_info

        t0 = time.time()
        result = run_symptom_recommendation(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            monitor,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.processed_message or ctx.sanitized_message,
            ctx.triage_result,
            self._client,
            user_agent=ctx.user_agent,
            client_ip=ctx.client_ip,
            merge_into_user_info=merge_into_user_info,
        )
        log_agent_step(
            self._trace_id,
            "PhysicalOrchestrator",
            "complete",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
        )
        return result

    def _route_ask(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.chat_ask_route import route_ask_category

        t0 = time.time()
        ask_state = route_ask_category(
            ctx.session,
            ctx.sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            self._client,
        )
        log_agent_step(
            self._trace_id,
            "AskAgent",
            "complete",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
        )
        if ask_state.response is not None:
            return ask_state.response
        if ask_state.triage_result:
            ctx.triage_result = ask_state.triage_result
        if ask_state.category == "Physical":
            ctx.triage_result = dict(ctx.triage_result or {})
            ctx.triage_result["category"] = "Physical"
            return self._route_physical(ctx, None)
        from src.services.medicine_discovery_routing import (
            cold_start_needs_recommendation_flow,
            session_is_medical_cold_start,
        )

        if session_is_medical_cold_start(
            ctx.session, ctx.sid
        ) and cold_start_needs_recommendation_flow(ctx.sanitized_message):
            ctx.triage_result = dict(ctx.triage_result or {})
            ctx.triage_result["category"] = "Physical"
            ctx.triage_result["subcategory"] = "medicine_discovery"
            logger.info("💊 初回セッション: オーケストレーターが Ask→Physical 推奨へ")
            return self._route_physical(ctx, None)
        return None

    def _enrich_concierge_intent(self, ctx: Any) -> None:
        from src.services.concierge_orchestrator import enrich_other_concierge_intent

        if not ctx.triage_result:
            return
        history = ctx.session.get("messages", [])[-10:]
        enriched = enrich_other_concierge_intent(
            ctx.triage_result,
            ctx.sanitized_message or ctx.user_message,
            self._client,
            conversation_history=history,
            session_id=ctx.sid,
            alt_texts=[
                t
                for t in (
                    getattr(ctx, "original_user_message", None),
                    ctx.user_message,
                )
                if t
            ],
        )
        ctx.triage_result = enriched
        if hasattr(ctx.session, "modified"):
            ctx.session["last_triage_result"] = enriched
            ctx.session.modified = True
        else:
            ctx.session["last_triage_result"] = enriched

    def _route_concierge(self, ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.chat_concierge_route import try_concierge_response

        t0 = time.time()
        resp = try_concierge_response(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.original_user_message or ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            self._client,
            monitor=monitor,
            processed_message=ctx.processed_message or ctx.sanitized_message,
        )
        log_agent_step(
            self._trace_id,
            "ConciergeAgent",
            "complete",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
            payload={"handled": resp is not None},
        )
        return resp

    def _route_store(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.agents.store_inquiry_agent import handle_store_inquiry

        if ctx.inappropriate_request_detected:
            return None
        t0 = time.time()
        resp = handle_store_inquiry(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.sanitized_message,
            self._client,
            ctx.triage_result,
            display_user_message=ctx.original_user_message or ctx.user_message,
        )
        log_agent_step(
            self._trace_id,
            "StoreInquiryAgent",
            "complete",
            sid=ctx.sid,
            ms=(time.time() - t0) * 1000,
            payload={"handled": resp is not None},
        )
        return resp

    def _route_inappropriate_drug_block(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.inappropriate_drug_block_route import (
            try_inappropriate_drug_block_response,
        )

        return try_inappropriate_drug_block_response(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.user_message or "",
            ctx.sanitized_message or ctx.user_message or "",
            ctx.triage_result,
            append_user=True,
        )

    def _route_emergency(self, ctx: Any) -> Optional[ResponseTuple]:
        from src.handlers.chat.emergency_dispatch import dispatch_emergency

        mod_label = None
        if ctx.triage_result:
            mod_label = ctx.triage_result.get("_moderation_label")
        return dispatch_emergency(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.sanitized_message,
            self._client,
            ctx.triage_result,
            moderation_label=mod_label,
            trace_id=self._trace_id,
        )


def try_orchestrator_route(ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
    if not is_agent_enabled():
        return None
    if not ctx.triage_result:
        return None
    orch = ChatOrchestrator(ctx.recommendation_client, trace_id=getattr(ctx, "trace_id", None))
    result = orch.route(ctx, monitor)
    if result.resolved and result.response:
        return result.response
    return None
