"""
チャット POST のメインオーケストレーション

chat_handler.handle_chat_post から委譲。各ステップは個別ルートモジュールが担当。
"""
from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.core.medicine_logic import client as openai_client
from src.handlers.chat.chat_llm_gate import check_llm_budget_block, setup_llm_request
from src.handlers.chat.chat_manual_reply import handle_manual_reply_when_off
from src.handlers.chat.chat_dev_triggers import try_dev_error_trigger
from src.handlers.chat.chat_post_init import empty_message_response, parse_incoming_message
from src.handlers.chat.chat_preprocess_route import preprocess_user_message
from src.handlers.chat.chat_session_route import (
    append_user_message_if_needed,
    apply_emotional_keyword_routing,
    handle_chat_end_if_requested,
    sync_messages_to_db_for_admin,
)
from src.services.session_manager import get_session_from_db
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


@dataclass
class ChatPostContext:
    """POST 処理中の可変コンテキスト"""

    session: Any
    client_info: ChatClientInfo
    sid: Optional[str]
    monitor: Any
    user_agent: str
    client_ip: str
    user_message: str = ""
    sanitized_message: str = ""
    processed_message: str = ""
    original_user_message: str = ""
    triage_result: Optional[Dict[str, Any]] = None
    inappropriate_request_detected: bool = False
    pending_route_is_question: Optional[bool] = None
    has_sleepiness_keyword: bool = False
    has_insomnia_keyword: bool = False
    trace_id: str = ""
    recommendation_client: OpenAI = field(default_factory=lambda: openai_client)


def run_chat_post_pipeline(
    session: Any,
    client_info: ChatClientInfo,
    message: str,
    sid: Optional[str],
    monitor: Any,
) -> ResponseTuple:
    """チャット POST の全ステップを実行し (body, status) を返す。"""
    ctx = ChatPostContext(
        session=session,
        client_info=client_info,
        sid=sid,
        monitor=monitor,
        user_agent=client_info.user_agent,
        client_ip=client_info.client_ip,
        trace_id=str(uuid.uuid4()),
    )

    logger.info("📨 POST処理開始 trace_id=%s", ctx.trace_id)
    ctx.user_message = parse_incoming_message(session, message)

    dev_trigger_resp = try_dev_error_trigger(
        session,
        sid,
        ctx.user_message,
        client_ip=ctx.client_ip,
        user_agent=ctx.user_agent,
    )
    if dev_trigger_resp is not None:
        return dev_trigger_resp

    if not ctx.user_message:
        resp = empty_message_response(
            session, sid, monitor, ctx.user_agent, ctx.client_ip
        )
        return resp if resp else ({"status": "ok", "message_count": 0}, 200)

    session.setdefault("messages", [])

    session_data_for_ai = get_session_from_db(sid) if sid else {}
    manual_resp = handle_manual_reply_when_off(
        session, client_info, sid, ctx.sanitized_message, session_data_for_ai
    )
    if manual_resp is not None:
        return manual_resp

    setup_llm_request(session, sid)
    budget_resp = check_llm_budget_block(session, sid)
    if budget_resp is not None:
        return budget_resp

    from src.agents.safety_gate import run_safety_gate_pre

    pre_gate, ctx.sanitized_message = run_safety_gate_pre(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.user_message,
        recommendation_client=ctx.recommendation_client,
    )
    if pre_gate.blocked and pre_gate.response:
        return pre_gate.response

    from src.handlers.chat.chat_triage import run_triage

    early_response, ctx.triage_result = run_triage(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.recommendation_client,
    )
    if early_response is not None:
        return early_response

    from src.agents.safety_gate import run_safety_gate

    post_gate = run_safety_gate(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.sanitized_message,
        triage_result=ctx.triage_result,
        recommendation_client=ctx.recommendation_client,
        phase="full",
    )
    if post_gate.blocked and post_gate.response:
        return post_gate.response

    ctx.original_user_message = ctx.user_message
    ctx.sanitized_message, ctx.processed_message = preprocess_user_message(
        session, sid, ctx.sanitized_message
    )

    from src.handlers.chat.chat_triage_follow_ups import run_triage_follow_ups

    early_resp, ctx.inappropriate_request_detected = run_triage_follow_ups(
        session,
        client_info,
        sid,
        ctx.sanitized_message,
        ctx.user_message,
        ctx.processed_message,
        ctx.triage_result,
        ctx.recommendation_client,
    )
    if early_resp is not None:
        return early_resp

    resp = _run_store_and_other_followups(ctx)
    if resp is not None:
        return resp

    apply_emotional_keyword_routing(
        session, ctx.triage_result, ctx.sanitized_message, phase="sleepiness"
    )
    append_user_message_if_needed(session, sid, client_info, ctx.original_user_message)

    from src.handlers.chat.chat_counseling_flow import run_counseling_flow

    counseling_response, ctx.triage_result = run_counseling_flow(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.processed_message,
        ctx.triage_result,
        ctx.recommendation_client,
    )
    if counseling_response is not None:
        return counseling_response

    apply_emotional_keyword_routing(
        session, ctx.triage_result, ctx.sanitized_message, phase="insomnia"
    )
    ctx.has_sleepiness_keyword = session.get("has_sleepiness_keyword", False)
    ctx.has_insomnia_keyword = session.get("has_insomnia_keyword", False)

    if ctx.triage_result:
        from src.handlers.chat.chat_confidence_route import check_triage_confidence

        conf_resp = check_triage_confidence(
            session,
            sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            ctx.recommendation_client,
        )
        if conf_resp is not None:
            return conf_resp

    _run_moderation_if_needed(ctx)

    from config.llm_flags import is_agent_enabled, is_agent_session_eligible

    if is_agent_enabled() and is_agent_session_eligible(sid):
        try:
            from src.handlers.chat_orchestrator import try_orchestrator_route

            orch_resp = try_orchestrator_route(ctx, monitor)
            if orch_resp is not None:
                return orch_resp
        except Exception as orch_err:
            logger.warning("⚠️ ChatOrchestrator をスキップ: %s", orch_err)
    elif ctx.triage_result:
        from src.handlers.chat.chat_category_route import route_triage_category

        cat_route = route_triage_category(
            session,
            sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            ctx.recommendation_client,
            inappropriate_request_detected=ctx.inappropriate_request_detected,
            has_sleepiness_keyword=ctx.has_sleepiness_keyword,
            has_insomnia_keyword=ctx.has_insomnia_keyword,
        )
        if cat_route.response is not None:
            return cat_route.response
        ctx.user_message = cat_route.user_message
        ctx.sanitized_message = cat_route.sanitized_message
        ctx.triage_result = cat_route.triage_result or ctx.triage_result
        if cat_route.is_question is not None:
            ctx.pending_route_is_question = cat_route.is_question

    session["last_trace_id"] = ctx.trace_id

    end_resp = handle_chat_end_if_requested(session, sid, ctx.sanitized_message)
    if end_resp is not None:
        return end_resp

    append_user_message_if_needed(session, sid, client_info, ctx.original_user_message)
    sync_messages_to_db_for_admin(session, sid, client_info)

    from src.handlers.chat.chat_question_route import handle_question_flow

    q_result = handle_question_flow(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.processed_message,
        ctx.recommendation_client,
        pending_route_is_question=ctx.pending_route_is_question,
    )
    if q_result.response is not None:
        return q_result.response

    is_question = q_result.is_question
    ctx.user_message = q_result.user_message
    ctx.sanitized_message = q_result.sanitized_message

    force_question_mode = session.get("should_handle_other_category", False)
    if not is_question and not force_question_mode:
        from src.handlers.chat.chat_symptom_route import run_symptom_recommendation
        from src.services.llm_metrics import merge_into_user_info

        return run_symptom_recommendation(
            session,
            client_info,
            sid,
            monitor,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.processed_message,
            ctx.triage_result,
            ctx.recommendation_client,
            user_agent=ctx.user_agent,
            client_ip=ctx.client_ip,
            merge_into_user_info=merge_into_user_info,
        )

    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)


def _run_moderation_if_needed(ctx: ChatPostContext) -> None:
    from src.agents.moderation_agent import run_moderation_agent, should_run_moderation
    from src.agents.safety_gate import _borderline_crisis_hint

    needs_review = _borderline_crisis_hint(ctx.sanitized_message)
    if not should_run_moderation(
        needs_llm_review=needs_review,
        triage_result=ctx.triage_result,
    ):
        return
    mod = run_moderation_agent(
        ctx.sanitized_message,
        ctx.recommendation_client,
        trace_id=ctx.trace_id,
        sid=ctx.sid,
    )
    label = (mod.get("label") or "safe").lower()
    if label == "crisis":
        ctx.triage_result = dict(ctx.triage_result or {})
        ctx.triage_result["category"] = "Emergency"
        ctx.triage_result["requires_immediate_action"] = True
    elif label == "inappropriate":
        ctx.inappropriate_request_detected = True


def _run_store_and_other_followups(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    store_inquiry_result = None
    if not ctx.inappropriate_request_detected:
        try:
            from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response

            store_resp = handle_store_inquiry_response(
                ctx.session,
                ctx.client_info,
                ctx.sid,
                ctx.sanitized_message,
                ctx.recommendation_client,
                ctx.triage_result,
                display_user_message=ctx.original_user_message,
            )
            if store_resp is not None:
                return store_resp
        except ImportError as e:
            logger.warning("⚠️ 店舗案内・遺失物関連機能のインポートに失敗: %s", e)
        except Exception as e:
            logger.error("❌ 店舗案内・遺失物関連機能でエラー: %s", e)
            traceback.print_exc()
    else:
        logger.info("⏭️ 不適切な要求が検出されたため、店舗案内処理をスキップ")

    if (
        store_inquiry_result is None
        and ctx.triage_result
        and ctx.triage_result.get("category") == "Other"
    ):
        from src.handlers.chat.chat_recommendation_followup import run_recommendation_followups

        followup = run_recommendation_followups(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.monitor,
            triage_result=ctx.triage_result,
            sanitized_message=ctx.sanitized_message,
            user_message=ctx.user_message,
            processed_message=ctx.processed_message,
            original_user_message=ctx.original_user_message,
            recommendation_client=ctx.recommendation_client,
        )
        if followup.response is not None:
            return followup.response
        if followup.sanitized_message is not None:
            ctx.sanitized_message = followup.sanitized_message
        if followup.user_message is not None:
            ctx.user_message = followup.user_message
        if followup.processed_message is not None:
            ctx.processed_message = followup.processed_message

        from src.handlers.chat.chat_other_counseling_route import run_other_unknown_counseling

        other_resp = run_other_unknown_counseling(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.processed_message,
            ctx.original_user_message,
            ctx.triage_result,
            ctx.recommendation_client,
        )
        if other_resp is not None:
            return other_resp
    return None
