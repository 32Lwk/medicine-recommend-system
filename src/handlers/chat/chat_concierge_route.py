"""
ConciergeAgent 早期ルート — 挨拶・メタ質問・雑談・Physical ハンドオフ
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.agents.concierge_agent import (
    build_concierge_payload,
    resolve_concierge_intent,
    should_concierge_handle,
    update_concierge_state,
)
from src.services.concierge_intent import should_reset_off_topic
from src.services.session_manager import (
    append_user_message,
    get_next_user_number,
    get_session_from_db,
    has_recent_concierge_reply_for_user,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _append_bot_message(session: Any, payload: Dict[str, Any]) -> dict:
    bot = {
        "type": "bot",
        "content": payload["content"],
        "concierge": True,
        "concierge_intent": payload.get("concierge_intent"),
        "content_format": payload.get("content_format", "text"),
        "timestamp": datetime.now().isoformat(),
        "uuid": str(uuid.uuid4()),
    }
    if payload.get("greeting"):
        bot["greeting"] = True
    if payload.get("concierge_handoff_to"):
        bot["concierge_handoff_to"] = payload["concierge_handoff_to"]
    session.setdefault("messages", []).append(bot)
    return bot


def _sync_session_db(
    session: Any,
    client_info: Any,
    sid: Optional[str],
) -> None:
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if not session_data:
        session_data = {
            "session_id": sid,
            "username": session.get("username", f"ユーザー{get_next_user_number()}"),
            "messages": list(session.get("messages", [])),
            "last_activity": datetime.now(),
            "client_ip": client_info.client_ip,
            "user_agent": client_info.user_agent,
            "user_attributes": session.get("user_attributes", {}),
            "session_active": True,
        }
    else:
        session_data["messages"] = list(session.get("messages", []))
        session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)


def _log_concierge_response(
    *,
    session_id: Optional[str],
    intent: str,
    content: str,
    llm_used: bool,
    user_input: str,
) -> None:
    try:
        from src.services.counseling.counseling_logger import log_counseling_response

        log_counseling_response(
            session_id=session_id,
            response_content=content,
            response_type=f"concierge_{intent}",
            category="Concierge",
            confidence=1.0,
            counseling_mode={"concierge_intent": intent, "llm_used": llm_used},
            user_input=user_input,
        )
    except Exception as exc:
        logger.debug("concierge log skipped: %s", exc)


def try_concierge_duplicate_skip(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
) -> Optional[ResponseTuple]:
    """トリアージ前に同一挨拶の重複 POST を即スキップ（LLM トリアージ回避）。"""
    text = (sanitized_message or user_message or "").strip()
    if not text or not has_recent_concierge_reply_for_user(session, text):
        return None
    if not should_concierge_handle(text, None):
        return None
    logger.info("⏭️ トリアージ前: 同一 Concierge 返信済みのためスキップ")
    if sid:
        try:
            from src.services.processing_mark import mark_phase
            from src.services.processing_status import set_processing_flow

            set_processing_flow(sid, "concierge")
            mark_phase(sid, "finalize")
        except Exception:
            pass
    _sync_session_db(session, client_info, sid)
    _mark_session_modified(session)
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)


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
) -> Optional[ResponseTuple]:
    text = (sanitized_message or user_message or "").strip()
    if not text or not should_concierge_handle(text, triage_result):
        return None

    if triage_result and triage_result.get("category") == "Other":
        from src.services.concierge_orchestrator import enrich_other_concierge_intent

        history_pre = session.get("messages", [])[-10:]
        triage_result = enrich_other_concierge_intent(
            triage_result,
            text,
            recommendation_client,
            conversation_history=history_pre,
            session_id=sid,
        )

    if has_recent_concierge_reply_for_user(session, text):
        logger.info("⏭️ 同一ユーザー発言への Concierge 返信済みのためスキップ")
        if sid:
            try:
                from src.services.processing_mark import mark_phase
                from src.services.processing_status import set_processing_flow

                set_processing_flow(sid, "concierge")
                mark_phase(sid, "finalize")
            except Exception:
                pass
        _sync_session_db(session, client_info, sid)
        _mark_session_modified(session)
        return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)

    history = session.get("messages", [])[-10:]
    intent = resolve_concierge_intent(
        text,
        session,
        triage_result=triage_result,
        client=recommendation_client,
        session_id=sid,
        conversation_history=history,
    )
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

    if not was_last_user_message(session, user_message or text):
        append_user_message(session, user_message or text)

    payload = build_concierge_payload(
        intent,
        text,
        recommendation_client,
        session_id=sid,
        history=history,
    )
    _append_bot_message(session, payload)
    update_concierge_state(
        session,
        intent,
        reset_off_topic=should_reset_off_topic(text),
    )
    _log_concierge_response(
        session_id=sid,
        intent=intent,
        content=payload["content"][:500],
        llm_used=bool(payload.get("llm_used")),
        user_input=text,
    )
    _mark_session_modified(session)

    _sync_session_db(session, client_info, sid)
    count = len(session.get("messages", []))
    logger.info("✅ Concierge 完了: %s messages", count)
    return ({"status": "ok", "message_count": count}, 200)
