"""
チャット POST のメインオーケストレーション

chat_handler.handle_chat_post から委譲。各ステップは個別ルートモジュールが担当。
"""
from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.core.language_utils import resolve_session_language
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
from src.utils.input_helpers import resolve_llm_user_text
from src.services.session_manager import resolve_session_snapshot
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
    routing: Any = None  # RoutingContext | None

    @property
    def llm_user_text(self) -> str:
        return resolve_llm_user_text(self.original_user_message, self.user_message)


def _load_session_snapshot_for_pipeline(sid: Optional[str]) -> dict:
    """LINE primed セッションはメモリのみ参照。"""
    from src.services.pipeline_perf import record_pipeline_perf

    snap = resolve_session_snapshot(sid) if sid else None
    if sid and str(sid).lower().startswith("line:"):
        record_pipeline_perf(session_db_source="memory" if snap else "memory_miss")
    elif sid:
        record_pipeline_perf(session_db_source="db")
    return snap or {}


def sync_routing_context(ctx: ChatPostContext) -> None:
    """トリアージ・履歴・ゲート状態を RoutingContext に同期する。"""
    from src.services.routing_context import RoutingContext

    ctx.routing = RoutingContext.build(
        ctx.session,
        ctx.sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.triage_result,
        pending_route_is_question=ctx.pending_route_is_question,
    )
    triage = ctx.routing.triage_result
    if triage:
        ctx.session["last_triage_result"] = triage


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
    from src.services.pipeline_perf import activate_pipeline_perf, mark_pipeline_step

    activate_pipeline_perf(sid)
    mark_pipeline_step("post_start")
    ctx.user_message = parse_incoming_message(session, message)
    mark_pipeline_step("parsed_message")

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
    session.pop("_user_attr_notice_appended", None)

    mark_pipeline_step("session_db_read")
    session_data_for_ai = _load_session_snapshot_for_pipeline(sid)
    mark_pipeline_step("after_get_session_db")
    manual_resp = handle_manual_reply_when_off(
        session, client_info, sid, ctx.user_message, session_data_for_ai
    )
    if manual_resp is not None:
        return manual_resp

    from src.handlers.line.line_session import count_bot_messages_in_session
    from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response

    bot_count_before = count_bot_messages_in_session(session)

    def _guard_return(resp: ResponseTuple) -> ResponseTuple:
        return finalize_pipeline_response(
            session,
            sid,
            client_info,
            bot_count_before,
            resp,
            recommendation_client=ctx.recommendation_client,
        )

    mark_pipeline_step("before_llm_setup")
    setup_llm_request(session, sid)
    budget_resp = check_llm_budget_block(session, sid)
    if budget_resp is not None:
        return _guard_return(budget_resp)

    mark_pipeline_step("before_security")
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
        return _guard_return(pre_gate.response)

    mark_pipeline_step("after_security")
    from src.services.line_user_memory import apply_profile_to_session, is_line_memory_session

    if is_line_memory_session(sid, session):
        from src.services.line_user_memory import resolve_memory_owner_sid

        owner = resolve_memory_owner_sid(sid, session)
        if owner:
            apply_profile_to_session(session, owner)

    from src.agents.memory_delete_agent import try_handle_memory_delete

    delete_resp = try_handle_memory_delete(
        session,
        sid,
        ctx.sanitized_message or ctx.user_message,
        ctx.recommendation_client,
    )
    if delete_resp is not None:
        sync_messages_to_db_for_admin(session, sid, client_info)
        return _guard_return(delete_resp)

    mark_pipeline_step("before_emoji_route")
    from src.handlers.chat.chat_emoji_route import try_emoji_pre_triage_route

    emoji_resp = try_emoji_pre_triage_route(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.sanitized_message or ctx.user_message,
        ctx.recommendation_client,
    )
    if emoji_resp is not None:
        return _guard_return(emoji_resp)

    mark_pipeline_step("before_triage")
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
        return _guard_return(early_response)

    mark_pipeline_step("after_triage")

    from src.services.medicine_discovery_routing import apply_cold_start_triage_override

    ctx.triage_result = apply_cold_start_triage_override(
        session,
        ctx.triage_result,
        ctx.user_message,
        sid=sid,
    )

    sync_routing_context(ctx)

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
        return _guard_return(post_gate.response)

    mark_pipeline_step("safety_gate_done")

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
        return _guard_return(early_resp)

    from config.llm_flags import is_agent_enabled

    if not is_agent_enabled():
        resp = _run_legacy_other_pre_orchestrator(ctx)
        if resp is not None:
            return _guard_return(resp)

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
        return _guard_return(counseling_response)

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
            client_info=client_info,
        )
        if conf_resp is not None:
            return _guard_return(conf_resp)
        if session.get("_last_triage_result"):
            ctx.triage_result = session["_last_triage_result"]
        sync_routing_context(ctx)

    mark_pipeline_step("confidence_gate_done")

    _run_moderation_if_needed(ctx)

    if is_agent_enabled():
        mark_pipeline_step("before_orchestrator")
        try:
            from src.handlers.chat_orchestrator import try_orchestrator_route

            orch_resp = try_orchestrator_route(ctx, monitor)
            if orch_resp is not None:
                return _guard_return(orch_resp)
        except Exception as orch_err:
            logger.warning("⚠️ ChatOrchestrator をスキップ: %s", orch_err)

        resp = _run_other_post_orchestrator_followups(ctx)
        if resp is not None:
            return _guard_return(resp)

    if session.get("_confidence_gate_concierge") and ctx.triage_result:
        from src.handlers.chat.chat_concierge_route import try_concierge_response

        concierge_resp = try_concierge_response(
            session,
            client_info,
            sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            ctx.recommendation_client,
            monitor=monitor,
            processed_message=ctx.processed_message,
            routing_ctx=ctx.routing,
        )
        session.pop("_confidence_gate_concierge", None)
        if concierge_resp is not None:
            return _guard_return(concierge_resp)
        if ctx.triage_result.get("category") == "Other":
            from src.handlers.chat.chat_other_counseling_route import (
                run_other_unknown_counseling,
            )

            counsel_resp = run_other_unknown_counseling(
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
            if counsel_resp is not None:
                return _guard_return(counsel_resp)
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
            return _guard_return(cat_route.response)
        ctx.user_message = cat_route.user_message
        ctx.sanitized_message = cat_route.sanitized_message
        ctx.triage_result = cat_route.triage_result or ctx.triage_result
        if cat_route.is_question is not None:
            ctx.pending_route_is_question = cat_route.is_question

    session["last_trace_id"] = ctx.trace_id

    end_resp = handle_chat_end_if_requested(session, sid, ctx.sanitized_message)
    if end_resp is not None:
        return _guard_return(end_resp)

    append_user_message_if_needed(session, sid, client_info, ctx.original_user_message)
    sync_messages_to_db_for_admin(session, sid, client_info)

    sync_routing_context(ctx)

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
        routing=ctx.routing,
    )
    if q_result.response is not None:
        return _guard_return(q_result.response)

    is_question = q_result.is_question
    ctx.user_message = q_result.user_message
    ctx.sanitized_message = q_result.sanitized_message

    if ctx.triage_result and ctx.triage_result.get("category") == "Emergency":
        from src.handlers.chat.emergency_dispatch import dispatch_emergency

        mod_label = ctx.triage_result.get("_moderation_label")
        emerg = dispatch_emergency(
            session,
            client_info,
            sid,
            ctx.sanitized_message,
            ctx.recommendation_client,
            ctx.triage_result,
            moderation_label=mod_label,
            trace_id=ctx.trace_id,
        )
        if emerg is not None:
            return _guard_return(emerg)

    force_question_mode = session.get("should_handle_other_category", False)
    if not is_question and not force_question_mode:
        from src.handlers.chat.emergency_dispatch import is_otc_flow_blocked
        from src.utils.input_helpers import (
            should_apply_unrecognized_symptom_gate,
            should_fallback_to_symptom_recommendation,
        )

        if is_otc_flow_blocked(session):
            from src.services.medical_emergency_templates import build_medical_emergency_html
            from src.services.sage_bot_response import build_bot_response
            from src.services.status_diagnosis_builder import build_emergency_status

            lang = resolve_session_language(session)
            lang = lang if lang in ("ja", "en", "ko", "zh") else "ja"
            html = build_medical_emergency_html(subtype="medical_self", language=lang)
            sage_diag = build_emergency_status(subtype="medical_self", language=lang).to_client_dict()
            session.setdefault("messages", []).append(
                build_bot_response(
                    session,
                    sid,
                    sage_diagnosis=sage_diag,
                    legacy_content=html,
                    emergency_detected=True,
                    otc_blocked=True,
                )
            )
            return _guard_return(
                (
                    {
                        "status": "ok",
                        "message_count": len(session.get("messages", [])),
                        "otc_blocked": True,
                    },
                    200,
                )
            )

        if not should_fallback_to_symptom_recommendation(
            ctx.triage_result,
            ctx.sanitized_message or ctx.user_message,
        ):
            return _guard_return(
                ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
            )

        from src.handlers.chat.chat_symptom_route import (
            run_symptom_recommendation,
            try_unrecognized_symptom_response,
        )
        from src.services.llm_metrics import merge_into_user_info

        if should_apply_unrecognized_symptom_gate(
            ctx.triage_result,
            ctx.sanitized_message or ctx.user_message,
        ):
            unrecognized_resp = try_unrecognized_symptom_response(
                session,
                client_info,
                sid,
                ctx.sanitized_message,
                ctx.user_message,
            )
            if unrecognized_resp is not None:
                return _guard_return(unrecognized_resp)

        return _guard_return(
            run_symptom_recommendation(
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
        )

    return _guard_return(
        ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
    )


async def run_chat_post_pipeline_async(
    session: Any,
    client_info: ChatClientInfo,
    message: str,
    sid: Optional[str],
    monitor: Any,
) -> ResponseTuple:
    """async エントリ（本体は sync pipeline を専用ワーカースレッドで実行）。"""
    import asyncio

    from src.services.chat_worker import get_chat_executor

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        get_chat_executor(),
        lambda: run_chat_post_pipeline(
            session,
            client_info,
            message,
            sid,
            monitor,
        ),
    )


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
        ctx.llm_user_text,
        ctx.recommendation_client,
        trace_id=ctx.trace_id,
        sid=ctx.sid,
    )
    label = (mod.get("label") or "safe").lower()
    if label == "crisis":
        ctx.triage_result = dict(ctx.triage_result or {})
        ctx.triage_result["category"] = "Emergency"
        ctx.triage_result["requires_immediate_action"] = True
        ctx.triage_result["_moderation_label"] = "crisis"
    elif label == "inappropriate":
        ctx.inappropriate_request_detected = True


def _try_concierge_before_store(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    """Other では Concierge を試すが、店舗案内確定時はスキップ。"""
    triage = ctx.triage_result or {}
    if triage.get("category") != "Other" or ctx.inappropriate_request_detected:
        return None
    from src.services.routing_context import evaluate_store_gate

    if evaluate_store_gate(
        ctx.original_user_message,
        ctx.sanitized_message,
        ctx.user_message,
        triage_result=triage,
        routing_ctx=ctx.routing,
    ):
        return None
    try:
        from src.services.concierge_orchestrator import enrich_other_concierge_intent
        from src.handlers.chat.chat_concierge_route import try_concierge_response

        history = (ctx.session.get("messages") or [])[-10:]
        from src.services.line_user_memory import is_line_memory_session

        memory_block = ""
        if is_line_memory_session(ctx.sid, ctx.session):
            from src.services.line_memory_context import get_llm_conversation_context

            history, _memory_block = get_llm_conversation_context(ctx.session, ctx.sid, limit=5)
        ctx.triage_result = enrich_other_concierge_intent(
            dict(triage),
            ctx.llm_user_text,
            ctx.recommendation_client,
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
            routing_ctx=ctx.routing,
        )
        return try_concierge_response(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.original_user_message or ctx.user_message,
            ctx.sanitized_message,
            ctx.triage_result,
            ctx.recommendation_client,
            processed_message=ctx.processed_message,
            routing_ctx=ctx.routing,
        )
    except Exception as exc:
        logger.warning("⚠️ Concierge 先行ルートをスキップ: %s", exc)
        return None


def _try_store_inquiry_response(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    try:
        from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response

        return handle_store_inquiry_response(
            ctx.session,
            ctx.client_info,
            ctx.sid,
            ctx.sanitized_message,
            ctx.recommendation_client,
            ctx.triage_result,
            display_user_message=ctx.original_user_message,
        )
    except ImportError as e:
        logger.warning("⚠️ 店舗案内・遺失物関連機能のインポートに失敗: %s", e)
    except Exception as e:
        logger.error("❌ 店舗案内・遺失物関連機能でエラー: %s", e)
        traceback.print_exc()
    return None


def _run_other_post_orchestrator_followups(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    """ChatOrchestrator 未解決時の Other フォールバック（店舗案内・推奨フォロー・不明要求カウンセリング）。"""
    if not ctx.triage_result or ctx.triage_result.get("category") != "Other":
        return None

    from src.services.routing_context import evaluate_store_gate

    if (
        not ctx.inappropriate_request_detected
        and evaluate_store_gate(
            ctx.original_user_message,
            ctx.sanitized_message,
            ctx.user_message,
            triage_result=ctx.triage_result,
            routing_ctx=ctx.routing,
        )
    ):
        store_resp = _try_store_inquiry_response(ctx)
        if store_resp is not None:
            return store_resp

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

    return run_other_unknown_counseling(
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


def _run_legacy_other_pre_orchestrator(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    """LLM_AGENT_ENABLED=OFF 時: 店舗→Concierge→Other フォールバック（レガシー経路）。"""
    from src.services.routing_context import evaluate_store_gate

    store_first = evaluate_store_gate(
        ctx.original_user_message,
        ctx.sanitized_message,
        ctx.user_message,
        triage_result=ctx.triage_result,
        routing_ctx=ctx.routing,
    )

    if store_first and not ctx.inappropriate_request_detected:
        store_resp = _try_store_inquiry_response(ctx)
        if store_resp is not None:
            return store_resp

    conc = _try_concierge_before_store(ctx)
    if conc is not None:
        return conc

    if not ctx.inappropriate_request_detected and not store_first:
        store_resp = _try_store_inquiry_response(ctx)
        if store_resp is not None:
            return store_resp
    elif ctx.inappropriate_request_detected:
        logger.info("⏭️ 不適切な要求が検出されたため、店舗案内処理をスキップ")

    return _run_other_post_orchestrator_followups(ctx)


def _run_store_and_other_followups(ctx: ChatPostContext) -> Optional[ResponseTuple]:
    """後方互換エイリアス（レガシー経路）。"""
    return _run_legacy_other_pre_orchestrator(ctx)
