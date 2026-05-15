"""
ChatOrchestrator — トリアージ後の9エージェント経路を一点に集約
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from config.llm_flags import is_agent_enabled, is_agent_session_eligible
from src.agents.protocols import HandoffResult
from src.agents.triage_agent import resolve_handoff
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


class ChatOrchestrator:
    def __init__(self, client: OpenAI, *, trace_id: Optional[str] = None):
        self._client = client
        self._trace_id = trace_id

    def route(
        self,
        ctx: Any,
        monitor: Any,
    ) -> Optional[ResponseTuple]:
        triage = ctx.triage_result
        if not triage:
            return None

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

        if handoff.stop or triage.get("category") == "Emergency":
            return None

        category = triage.get("category", "Other")
        confidence = float(triage.get("confidence") or 1.0)

        if category == "Emotional" and confidence >= 0.5:
            return self._route_emotional(ctx)

        if category == "Physical":
            return self._route_physical(ctx, monitor)

        if category == "Ask":
            return self._route_ask(ctx)

        if category == "Other":
            return self._route_store(ctx)

        return None

    def _mark_step(self, sid: Optional[str], category: str) -> None:
        try:
            from src.services.processing_status import mark_processing_step

            step = _AGENT_STEP_MAP.get(category, "triage")
            mark_processing_step(sid, step)
        except Exception as e:
            logger.debug("mark_processing_step skipped: %s", e)

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
        return None

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


def try_orchestrator_route(ctx: Any, monitor: Any) -> Optional[ResponseTuple]:
    if not is_agent_enabled():
        return None
    if not is_agent_session_eligible(ctx.sid):
        return None
    if not ctx.triage_result:
        return None
    orch = ChatOrchestrator(ctx.recommendation_client, trace_id=getattr(ctx, "trace_id", None))
    return orch.route(ctx, monitor)
