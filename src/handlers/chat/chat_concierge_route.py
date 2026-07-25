"""
ConciergeAgent 早期ルート — 挨拶・メタ質問・雑談・Physical ハンドオフ
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.agents.concierge_agent import (
    build_concierge_payload,
    resolve_concierge_intent,
    should_concierge_handle,
    update_concierge_state,
)
from src.services.concierge_intent import should_reset_off_topic
from src.utils.input_helpers import resolve_llm_user_text
from src.services.session_manager import (
    append_user_message,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _append_bot_message(session: Any, payload: Dict[str, Any], sid: Optional[str] = None) -> dict:
    from src.services.sage_bot_response import build_bot_response

    legacy_content = payload["content"]
    sage_diag = payload.get("sage_diagnosis")
    bot = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        concierge=True,
        concierge_intent=payload.get("concierge_intent"),
        content_format=payload.get("content_format", "text"),
        uuid=str(uuid.uuid4()),
    )
    if payload.get("greeting"):
        bot["greeting"] = True
    if payload.get("concierge_handoff_to"):
        bot["concierge_handoff_to"] = payload["concierge_handoff_to"]
    if payload.get("line_flex"):
        bot["line_flex"] = payload["line_flex"]
    session.setdefault("messages", []).append(bot)
    return bot


def _resolve_sync_username(session: Any, sid: str | None, existing: dict | None = None) -> str:
    name = session.get("username")
    if name:
        return str(name)
    if existing:
        existing_name = existing.get("username")
        if existing_name:
            return str(existing_name)
        profile = existing.get("line_profile") or {}
        display = profile.get("displayName")
        if display:
            return str(display)
    return f"ユーザー{get_next_user_number()}"


def _sync_session_db(
    session: Any,
    client_info: Any,
    sid: Optional[str],
) -> None:
    if not sid:
        return
    from src.handlers.line.line_session import is_line_session_id
    from src.utils.jst_datetime import now_jst_iso

    if is_line_session_id(sid):
        from src.services.session_manager import (
            get_line_session_admin_snapshot,
            maybe_persist_session_activity,
            touch_session_in_memory,
        )

        existing = get_line_session_admin_snapshot(sid) or {}
        session_data = dict(existing)
        session_data.update({
            "session_id": sid,
            "username": _resolve_sync_username(session, sid, existing),
            "messages": list(session.get("messages", [])),
            "last_activity": now_jst_iso(),
            "client_ip": client_info.client_ip,
            "user_agent": client_info.user_agent,
            "user_attributes": session.get("user_attributes") or existing.get("user_attributes") or {},
            "session_active": True,
        })
        if session.get("concierge_state") is not None:
            session_data["concierge_state"] = session.get("concierge_state")
        if session.get("last_triage_result") is not None:
            session_data["last_triage_result"] = session.get("last_triage_result")
        touch_session_in_memory(sid, session_data)
        maybe_persist_session_activity(sid, session_data)
        return
    session_data = get_session_from_db(sid)
    if not session_data:
        session_data = {
            "session_id": sid,
            "username": _resolve_sync_username(session, sid),
            "messages": list(session.get("messages", [])),
            "last_activity": now_jst_iso(),
            "client_ip": client_info.client_ip,
            "user_agent": client_info.user_agent,
            "user_attributes": session.get("user_attributes", {}),
            "session_active": True,
        }
    else:
        session_data["messages"] = list(session.get("messages", []))
        session_data["last_activity"] = now_jst_iso()
        if not session_data.get("username"):
            session_data["username"] = _resolve_sync_username(session, sid, session_data)
    save_session_to_db(sid, session_data)


def _log_concierge_response(
    *,
    session: Any,
    session_id: Optional[str],
    intent: str,
    content: str,
    llm_used: bool,
    user_input: str,
    conversation_history: Optional[list] = None,
    concierge_intent_source: Optional[str] = None,
) -> None:
    try:
        from src.services.counseling.counseling_logger import log_counseling_response

        counseling_mode: Dict[str, Any] = {
            "concierge_intent": intent,
            "llm_used": llm_used,
        }
        if concierge_intent_source:
            counseling_mode["concierge_intent_source"] = concierge_intent_source

        log_counseling_response(
            session_id=session_id,
            response_content=content,
            response_type=f"concierge_{intent}",
            category="Concierge",
            confidence=1.0,
            counseling_mode=counseling_mode,
            user_input=user_input,
            conversation_history=conversation_history,
            session=session,
        )
    except Exception as exc:
        logger.debug("concierge log skipped: %s", exc)


def _concierge_already_answered_user(session: Any, user_content: str) -> bool:
    """同一ユーザー発言に対する Concierge 返信が直前に済んでいれば二重 POST を抑止。"""
    messages = session.get("messages") or []
    if len(messages) < 2:
        return False
    last = messages[-1]
    if last.get("type") != "bot" or not last.get("concierge") or not last.get("greeting"):
        return False
    for msg in reversed(messages[:-1]):
        if msg.get("type") == "user":
            return msg.get("content") == user_content
        if msg.get("type") == "bot" and not msg.get("user_info_notification"):
            return False
    return False


def try_concierge_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Optional[Dict[str, Any]],
    recommendation_client: OpenAI,
    *,
    monitor: Any = None,
    processed_message: str = "",
    routing_ctx: Any = None,
) -> Optional[ResponseTuple]:
    from src.services.llm_unavailability import should_block_llm_dependent_reply

    if should_block_llm_dependent_reply(session):
        logger.info("Skipping Concierge: LLM infrastructure degraded sid=%s", sid)
        return None

    router_dispatch = bool((triage_result or {}).get("_intent_router_dispatch"))
    if router_dispatch:
        from src.dialogue.session_ops import try_answer_pending_delete_cancel

        cancel_resp = try_answer_pending_delete_cancel(session, sid, sanitized_message or user_message)
        if cancel_resp is not None:
            return cancel_resp

    routing_text = (sanitized_message or user_message or "").strip()
    llm_text = resolve_llm_user_text(user_message=user_message)
    alt_texts = [t for t in (user_message, processed_message, sanitized_message) if t]
    from src.services.routing_context import evaluate_store_gate

    if routing_text and evaluate_store_gate(
        routing_text,
        *alt_texts,
        triage_result=triage_result,
        routing_ctx=routing_ctx,
    ):
        return None
    if not routing_text or not should_concierge_handle(
        routing_text,
        triage_result,
        alt_texts=alt_texts,
    ):
        return None

    user_turn_text = user_message or llm_text
    if _concierge_already_answered_user(session, user_turn_text):
        count = len(session.get("messages", []))
        logger.info("⏭️ Concierge 二重 POST 抑止: user=%r", user_turn_text[:40])
        return ({"status": "ok", "message_count": count}, 200)

    if (
        triage_result
        and triage_result.get("category") == "Other"
        and (
            not triage_result.get("concierge_intent")
            or triage_result.get("concierge_intent") == "general_other"
        )
    ):
        from src.services.concierge_orchestrator import enrich_other_concierge_intent

        from src.dialogue.history import resolve_concierge_history_with_fallback

        history_pre = resolve_concierge_history_with_fallback(session, sid)
        triage_result = enrich_other_concierge_intent(
            triage_result,
            llm_text,
            recommendation_client,
            conversation_history=history_pre,
            session_id=sid,
            session=session,
            alt_texts=[user_message, processed_message],
            routing_ctx=routing_ctx,
        )

    if not was_last_user_message(session, user_message or llm_text):
        append_user_message(session, user_message or llm_text)

    from src.core.language_utils import update_session_language_from_message

    update_session_language_from_message(session, user_message or llm_text or routing_text)

    from src.dialogue.history import (
        resolve_concierge_history_with_fallback,
        resolve_counseling_history_with_fallback,
    )

    history = resolve_concierge_history_with_fallback(session, sid)
    log_history = resolve_counseling_history_with_fallback(session, sid)
    from src.services.pipeline_perf import mark_pipeline_step

    mark_pipeline_step("concierge_resolve_intent_start")
    intent = resolve_concierge_intent(
        routing_text,
        session,
        triage_result=triage_result,
        client=recommendation_client,
        session_id=sid,
        conversation_history=history,
        routing_ctx=routing_ctx,
        llm_user_text=llm_text,
    )
    mark_pipeline_step("concierge_resolve_intent_end")
    if intent is None:
        return None

    logger.info("🛎️ ConciergeAgent: intent=%s", intent)

    if sid:
        try:
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(sid, "concierge")
            mark_processing_step(sid, "concierge")
        except Exception:
            pass

    mark_pipeline_step("concierge_build_payload_start")
    payload = build_concierge_payload(
        intent,
        llm_text,
        recommendation_client,
        session_id=sid,
        history=history,
    )
    from src.services.concierge_i18n import apply_concierge_payload_i18n

    payload = apply_concierge_payload_i18n(session, payload, session_id=sid)
    mark_pipeline_step("concierge_build_payload_end")
    _append_bot_message(session, payload, sid)
    from src.services.concierge_execution_sync import sync_concierge_execution_metadata

    sync_concierge_execution_metadata(
        session,
        sid=sid,
        resolved_intent=intent,
        triage_result=triage_result,
        user_text=llm_text,
        response_preview=str(payload.get("content") or "")[:500],
    )
    update_concierge_state(
        session,
        intent,
        reset_off_topic=should_reset_off_topic(routing_text),
    )
    try:
        from src.dialogue.context import mirror_concierge_intent

        mirror_concierge_intent(session, sid, intent)
    except Exception:
        logger.debug("mirror_concierge_intent skipped", exc_info=True)
    _log_concierge_response(
        session=session,
        session_id=sid,
        intent=intent,
        content=payload["content"][:500],
        llm_used=bool(payload.get("llm_used")),
        user_input=llm_text,
        conversation_history=log_history,
        concierge_intent_source=(triage_result or {}).get("concierge_intent_source"),
    )
    _mark_session_modified(session)

    _sync_session_db(session, client_info, sid)
    count = len(session.get("messages", []))
    logger.info("✅ Concierge 完了: %s messages", count)
    return ({"status": "ok", "message_count": count}, 200)
