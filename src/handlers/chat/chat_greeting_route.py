"""
挨拶の早期応答（LLMカウンセリング経路より前に処理）
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.chat_response_service import build_greeting_response
from src.services.input_classifier import classify_input
from src.services.session_manager import (
    append_user_message,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _already_replied_to_user(session: Any, user_content: str) -> bool:
    """同一ユーザー発言に対する bot 返信が既にあれば True（再送抑止）。"""
    messages = session.get("messages") or []
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("type") != "user":
            continue
        if msg.get("content") != user_content:
            continue
        if i + 1 < len(messages) and messages[i + 1].get("type") == "bot":
            return True
    return False


def try_greeting_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
) -> Optional[ResponseTuple]:
    """
    純粋な挨拶なら定型応答を返す。該当しなければ None。
    """
    text = (user_message or "").strip()
    if not text or classify_input(text) != "greeting":
        return None

    if _already_replied_to_user(session, text):
        logger.info("⏭️ 挨拶返信済みのためスキップ: %s", text)
        return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)

    logger.info("👋 挨拶の早期応答: %s", text)

    if sid:
        try:
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(sid, "greeting")
            mark_processing_step(sid, "counseling")
        except Exception:
            pass

    if not was_last_user_message(session, text):
        append_user_message(session, text)

    greeting_response = build_greeting_response(text)
    bot_response = {
        "type": "bot",
        "content": greeting_response,
        "greeting": True,
        "timestamp": datetime.now().isoformat(),
        "uuid": str(uuid.uuid4()),
    }
    session.setdefault("messages", []).append(bot_response)
    if hasattr(session, "modified"):
        session.modified = True

    if sid:
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

    message_count = len(session.get("messages", []))
    logger.info("✅ 挨拶の早期応答完了: %s messages", message_count)
    return ({"status": "ok", "message_count": message_count}, 200)
