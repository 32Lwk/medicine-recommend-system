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


def _try_session_ops_handler(
    session: Any,
    sid: Optional[str],
    user_text: str,
    client: Any,
    *,
    triage_result: Optional[Dict[str, Any]] = None,
    phase: str = "fast",
) -> Optional[ResponseTuple]:
    """v2 ON 時は dialogue SessionOps、OFF 時は SessionAgent（Wave 1a 境界）。"""
    from src.dialogue.pipeline import try_session_ops_route

    v2_resp = try_session_ops_route(
        session,
        sid,
        user_text,
        client,
        triage_result=triage_result,
        phase=phase,
    )
    if v2_resp is not None:
        return v2_resp

    from config.llm_flags import is_chat_pipeline_v2_for_session

    if is_chat_pipeline_v2_for_session(sid):
        return None

    from src.agents.session_agent import try_handle_session_request

    return try_handle_session_request(
        session,
        sid,
        user_text,
        client,
        triage_result=triage_result,
    )


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
        sub = str(triage.get("subcategory") or "").lower()
        from src.utils.input_helpers import has_fever_signal

        if "fever" in sub or has_fever_signal(ctx.user_message):
            ctx.session["_fever_context_active"] = True

    try:
        from src.dialogue.sync_legacy import sync_dialogue_legacy_mirrors, mark_correction_in_dialogue_state

        sync_dialogue_legacy_mirrors(ctx.session, ctx.sid)
        mark_correction_in_dialogue_state(ctx.session, ctx.sid, ctx.user_message)
    except Exception:
        logger.debug("sync_dialogue_legacy_mirrors skipped", exc_info=True)


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

    logger.info("📨 POST処理開始 trace_id=%s sid=%s", ctx.trace_id, sid)
    from src.services.pipeline_perf import activate_pipeline_perf, mark_pipeline_step
    from src.handlers.line.line_session import count_bot_messages_in_session
    from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response
    from src.utils.session_sid import bind_request_session_sid

    bind_request_session_sid(session, sid)
    activate_pipeline_perf(sid)
    mark_pipeline_step("post_start")
    session.pop("_router_dispatch_handled_turn", None)
    session.pop("_router_dispatch_attempted", None)

    bot_count_before = count_bot_messages_in_session(session)

    def _guard_return(resp: ResponseTuple) -> ResponseTuple:
        final = finalize_pipeline_response(
            session,
            sid,
            client_info,
            bot_count_before,
            resp,
            recommendation_client=ctx.recommendation_client,
            user_message=ctx.original_user_message or ctx.user_message,
        )
        try:
            from src.dialogue.adapters.web_sse import record_pipeline_envelope

            record_pipeline_envelope(session, sid, final)
        except Exception:
            logger.debug("record_pipeline_envelope skipped", exc_info=True)
        return final

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
        return _guard_return(dev_trigger_resp)

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
        return _guard_return(manual_resp)

    from src.agents.session_agent import probe_session_admin_intent

    if probe_session_admin_intent(ctx.user_message):
        session_admin_resp = _try_session_ops_handler(
            session,
            sid,
            ctx.user_message,
            ctx.recommendation_client,
            phase="admin_probe",
        )
        if session_admin_resp is not None:
            sync_messages_to_db_for_admin(session, sid, client_info)
            return _guard_return(session_admin_resp)

    mark_pipeline_step("before_llm_setup")
    setup_llm_request(session, sid)
    budget_resp = check_llm_budget_block(session, sid)
    if budget_resp is not None:
        return _guard_return(budget_resp)

    from src.services.llm_unavailability import try_respond_when_openai_unconfigured

    openai_guard_resp = try_respond_when_openai_unconfigured(
        session,
        sid,
        user_message=ctx.original_user_message or ctx.user_message,
    )
    if openai_guard_resp is not None:
        return _guard_return(openai_guard_resp)

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

    from src.handlers.chat.chat_echo_guard import (
        build_echo_guard_response,
        detect_echo_user_input,
    )

    is_echo, echo_reason = detect_echo_user_input(session, ctx.user_message)
    if is_echo:
        try:
            from src.utils.structured_logger import log_counseling_detail

            log_counseling_detail(
                session_id=sid,
                echo_detected=True,
                echo_reason=echo_reason,
                user_input=ctx.user_message[:200],
            )
        except Exception:
            logger.debug("echo_detected log skipped", exc_info=True)
        bot = build_echo_guard_response(session, sid)
        session.setdefault("messages", []).append(bot)
        return _guard_return(
            {"status": "ok", "message_count": len(session.get("messages", []))},
            200,
        )

    from src.services.line_user_memory import apply_profile_to_session, is_line_memory_session

    if is_line_memory_session(sid, session):
        from src.services.line_user_memory import resolve_memory_owner_sid

        owner = resolve_memory_owner_sid(sid, session)
        if owner:
            apply_profile_to_session(session, owner)

    session_fast_resp = _try_session_ops_handler(
        session,
        sid,
        ctx.sanitized_message or ctx.user_message,
        ctx.recommendation_client,
        phase="fast",
    )
    if session_fast_resp is not None:
        sync_messages_to_db_for_admin(session, sid, client_info)
        return _guard_return(session_fast_resp)

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

    try:
        from src.dialogue.routing.shadow import schedule_shadow_observation

        schedule_shadow_observation(
            session,
            sid,
            ctx.sanitized_message or ctx.user_message,
            ctx.triage_result,
            ctx.recommendation_client,
        )
    except Exception:
        logger.debug("intent_router_shadow skipped", exc_info=True)

    session_triage_resp = _try_session_ops_handler(
        session,
        sid,
        ctx.sanitized_message or ctx.user_message,
        ctx.recommendation_client,
        triage_result=ctx.triage_result,
        phase="triage",
    )
    if session_triage_resp is not None:
        sync_messages_to_db_for_admin(session, sid, client_info)
        return _guard_return(session_triage_resp)

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

    mark_pipeline_step("after_triage_follow_ups")

    from config.llm_flags import is_agent_enabled

    if not is_agent_enabled():
        from config.llm_flags import is_chat_pipeline_v2_for_session

        if not is_chat_pipeline_v2_for_session(sid):
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

    mark_pipeline_step("after_counseling_flow")

    apply_emotional_keyword_routing(
        session, ctx.triage_result, ctx.sanitized_message, phase="insomnia"
    )
    ctx.has_sleepiness_keyword = session.get("has_sleepiness_keyword", False)
    ctx.has_insomnia_keyword = session.get("has_insomnia_keyword", False)

    _run_moderation_if_needed(ctx)

    mark_pipeline_step("moderation_done")

    try:
        from config.llm_flags import is_medicine_side_effect_qa_enabled
        from src.services.medicine_qa_routing import (
            get_medicine_qa_session_context,
            infer_medicine_qa_focuses,
            is_medicine_information_question,
            should_use_medicine_qa_unified,
        )
        from src.services.medicine_side_effect_routing import is_medicine_side_effect_route
        from src.services.medicine_qa_eligibility import (
            MedicineQaRoute,
            resolve_medicine_qa_route,
            should_route_medicine_information_qa,
        )

        user_msg = ctx.sanitized_message or ctx.user_message
        qa_ctx = get_medicine_qa_session_context(session, sid)
        mark_pipeline_step("before_medicine_qa_route")
        route_decision = resolve_medicine_qa_route(
            user_msg,
            session=session,
            triage_result=ctx.triage_result,
            conversation_history=qa_ctx["conversation_history"],
            recommended_medicines=qa_ctx["recommended_medicines"],
            client=ctx.recommendation_client,
        )
        skip_focus_llm = route_decision.route in (
            MedicineQaRoute.CONCIERGE,
            MedicineQaRoute.PHYSICAL,
        )
        focuses = infer_medicine_qa_focuses(
            user_msg,
            conversation_history=qa_ctx["conversation_history"],
            recommended_medicines=qa_ctx["recommended_medicines"],
            user_attributes=qa_ctx["user_attributes"],
            use_llm_enrichment=not skip_focus_llm,
        )
        mark_pipeline_step("after_medicine_qa_route")

        if is_medicine_information_question(
            user_msg,
            conversation_history=qa_ctx["conversation_history"],
            recommended_medicines=qa_ctx["recommended_medicines"],
        ) and should_route_medicine_information_qa(
            user_msg,
            session=session,
            triage_result=ctx.triage_result,
            conversation_history=qa_ctx["conversation_history"],
            recommended_medicines=qa_ctx["recommended_medicines"],
            client=ctx.recommendation_client,
        ):
            from src.handlers.chat.medicine_context_handlers import (
                handle_medicine_information_qa,
            )

            logger.info("💬 medicine_qa early route (information question)")
            mark_pipeline_step("medicine_qa_early_route_start")
            resp = _guard_return(
                handle_medicine_information_qa(
                    session,
                    client_info,
                    sid,
                    ctx.original_user_message or user_msg,
                )
            )
            mark_pipeline_step("medicine_qa_early_route_end")
            return resp
        if is_medicine_side_effect_qa_enabled(sid) and is_medicine_side_effect_route(user_msg):
            if should_use_medicine_qa_unified(focuses, user_message=user_msg):
                from src.handlers.chat.medicine_context_handlers import (
                    handle_medicine_information_qa,
                )

                logger.info("💬 medicine_qa early route (multi-focus side effect)")
                return _guard_return(
                    handle_medicine_information_qa(
                        session,
                        client_info,
                        sid,
                        ctx.original_user_message or user_msg,
                    )
                )
            from src.handlers.chat.medicine_side_effect_handlers import (
                handle_medicine_side_effect_qa,
            )

            logger.info("💊 medicine_side_effect_qa early route")
            return _guard_return(
                handle_medicine_side_effect_qa(
                    session,
                    client_info,
                    sid,
                    ctx.original_user_message or user_msg,
                )
            )
    except Exception:
        logger.debug("medicine_side_effect_qa early route skipped", exc_info=True)

    try:
        from src.services.medicine_context_routing import resolve_medicine_context_route

        med_ctx_route = resolve_medicine_context_route(
            session,
            sid,
            ctx.sanitized_message or ctx.user_message,
            client=ctx.recommendation_client,
            triage_result=ctx.triage_result,
        )
        if med_ctx_route == "followup_qa":
            from src.handlers.chat.medicine_context_handlers import handle_medicine_followup_qa

            logger.info("🏃 medicine_context early: followup_qa")
            return _guard_return(
                handle_medicine_followup_qa(
                    session,
                    client_info,
                    sid,
                    ctx.original_user_message or ctx.user_message,
                )
            )
        if med_ctx_route == "symptom_prompt":
            from src.handlers.chat.medicine_context_handlers import handle_sports_symptom_prompt

            logger.info("🏃 medicine_context early: symptom_prompt")
            return _guard_return(
                handle_sports_symptom_prompt(
                    session,
                    sid,
                    ctx.original_user_message or ctx.user_message,
                )
            )
        if med_ctx_route == "cold_symptom_chip_prompt":
            from src.handlers.chat.medicine_context_handlers import handle_cold_symptom_chip_prompt

            logger.info("🤧 medicine_context early: cold_symptom_chip_prompt")
            return _guard_return(
                handle_cold_symptom_chip_prompt(
                    session,
                    sid,
                    ctx.original_user_message or ctx.user_message,
                )
            )
        if med_ctx_route == "cold_start_recommend":
            logger.info("💊 medicine_context early: cold_start_recommend → Physical")
            ctx.triage_result = dict(ctx.triage_result or {})
            ctx.triage_result["category"] = "Physical"
            ctx.triage_result["subcategory"] = "medicine_discovery"
            session["last_triage_result"] = ctx.triage_result
            sync_routing_context(ctx)
    except Exception:
        logger.debug("medicine_context early route skipped", exc_info=True)

    from src.handlers.chat.chat_question_route import try_qa_gate_concierge_response

    concierge_pre = try_qa_gate_concierge_response(
        session,
        client_info,
        sid,
        ctx.user_message,
        ctx.sanitized_message,
        ctx.recommendation_client,
        triage_result=ctx.triage_result,
        routing=ctx.routing,
    )
    if concierge_pre is not None:
        return _guard_return(concierge_pre)

    if is_agent_enabled():
        mark_pipeline_step("before_orchestrator")
        try:
            from config.llm_flags import is_intent_router_dispatch_enabled

            if is_intent_router_dispatch_enabled(sid):
                from src.dialogue.dispatcher import try_agent_dispatch

                dispatch_resp = try_agent_dispatch(ctx, monitor)
                if dispatch_resp is not None:
                    session.pop("triage_clarify_sent", None)
                    return _guard_return(dispatch_resp)
                dec = session.get("_intent_router_dispatch")
                if dec or (ctx.triage_result or {}).get("_intent_router_dispatch"):
                    logger.info(
                        "dispatch_none_orchestrator_fallback sid=%s router=%s triage_cat=%s",
                        sid,
                        dec,
                        (ctx.triage_result or {}).get("category"),
                    )
        except Exception:
            logger.debug("intent_router_dispatch skipped", exc_info=True)

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

    from src.handlers.chat.llm_pipeline_guard import try_llm_pipeline_short_circuit

    short_circuit = try_llm_pipeline_short_circuit(
        session,
        sid,
        ctx.triage_result,
        user_message=ctx.user_message,
    )
    if short_circuit is not None:
        return _guard_return(short_circuit)

    if is_agent_enabled():
        if not _legacy_trim_blocks_path(ctx, "orchestrator"):
            try:
                from src.handlers.chat_orchestrator import try_orchestrator_route

                orch_resp = try_orchestrator_route(ctx, monitor)
                if orch_resp is not None:
                    mark_pipeline_step("orchestrator_end")
                    return _guard_return(orch_resp)
            except Exception as orch_err:
                logger.warning("⚠️ ChatOrchestrator をスキップ: %s", orch_err)

        mark_pipeline_step("orchestrator_end")

        if not _legacy_trim_blocks_path(ctx, "other_post_orchestrator"):
            resp = _run_other_post_orchestrator_followups(ctx)
            if resp is not None:
                return _guard_return(resp)

    if session.get("_confidence_gate_concierge") and ctx.triage_result:
        if _legacy_trim_blocks_path(ctx, "confidence_gate_concierge"):
            session.pop("_confidence_gate_concierge", None)
        else:
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
        if not _legacy_trim_blocks_path(ctx, "route_triage_category"):
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

        from src.handlers.chat.chat_question_route import try_qa_gate_concierge_response

        concierge_gate = try_qa_gate_concierge_response(
            session,
            client_info,
            sid,
            ctx.user_message,
            ctx.sanitized_message,
            ctx.recommendation_client,
            triage_result=ctx.triage_result,
            routing=ctx.routing,
        )
        if concierge_gate is not None:
            return _guard_return(concierge_gate)

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
        from config.llm_flags import is_chat_pipeline_v2_for_session

        if is_chat_pipeline_v2_for_session(ctx.sid):
            from src.dialogue.history import resolve_concierge_history_with_fallback

            history = resolve_concierge_history_with_fallback(ctx.session, ctx.sid)
        else:
            history = (ctx.session.get("messages") or [])[-10:]
            from src.services.line_user_memory import is_line_memory_session

            if is_line_memory_session(ctx.sid, ctx.session):
                from src.services.line_memory_context import get_llm_conversation_context

                history, _memory_block = get_llm_conversation_context(
                    ctx.session, ctx.sid, limit=5
                )
        ctx.triage_result = enrich_other_concierge_intent(
            dict(triage),
            ctx.llm_user_text,
            ctx.recommendation_client,
            conversation_history=history,
            session_id=ctx.sid,
            session=ctx.session,
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


def _legacy_fallback_allow_reason(ctx: ChatPostContext) -> str:
    """TRIM ON 時に legacy 経路を許可する理由（観測用）。"""
    dec = ctx.session.get("_intent_router_dispatch")
    if isinstance(dec, dict):
        route = dec.get("primary_route")
        if route in (None, "", "Unknown"):
            return "unknown_route"
        if dec.get("sub_route") == "clarification":
            return "clarification"
        if ctx.session.get("_router_dispatch_attempted") and not ctx.session.get(
            "_router_dispatch_handled_turn"
        ):
            return "handler_fallback"
    if not dec and not (ctx.triage_result or {}).get("_intent_router_dispatch"):
        return "no_router_decision"
    return "safety_fallback"


def _legacy_trim_blocks_path(ctx: ChatPostContext, path: str) -> bool:
    """
    PRIMARY + LEGACY_FALLBACK_TRIM 時、dispatch 成功後の legacy 再実行をブロック。
  Unknown / clarification / handler None は False（許可）を返す。
    """
    from config.llm_flags import is_legacy_fallback_trim_enabled

    if not is_legacy_fallback_trim_enabled(ctx.sid):
        return False

    if ctx.session.get("_router_dispatch_handled_turn"):
        if path == "route_triage_category":
            logger.info(
                "legacy_category_route_skipped sid=%s reason=dispatch_handled",
                ctx.sid,
            )
        else:
            logger.info(
                "legacy_fallback_trimmed sid=%s path=%s reason=dispatch_handled",
                ctx.sid,
                path,
            )
        return True

    reason = _legacy_fallback_allow_reason(ctx)
    logger.info(
        "legacy_fallback_allowed sid=%s path=%s reason=%s",
        ctx.sid,
        path,
        reason,
    )
    return False


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
