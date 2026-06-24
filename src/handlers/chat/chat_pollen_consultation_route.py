"""環境アレルギー（花粉症など）の相談入口 — 症状確認カウンセリング"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from src.services.session_manager import (
    append_user_message,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

_ALLERGY_INITIAL_QUESTIONS = [
    "鼻水・くしゃみ・目のかゆみ・鼻づまりのうち、いちばんつらいものを教えてください",
]


def build_allergy_entry_response(user_message: str) -> str:
    """相談入口向け — 窓口説明ではなく症状確認を促す。"""
    text = (user_message or "").strip()
    if "花粉" in text:
        opener = "花粉でお困りなんですね。"
    else:
        opener = "アレルギーでお困りなんですね。"
    return f"{opener}{_ALLERGY_INITIAL_QUESTIONS[0]}。"


def run_otc_allergy_consultation_entry(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    recommendation_client: Any,
) -> tuple:
    """「花粉症です」など — 推奨せず症状を聞くカウンセリング返信。"""
    from src.services.counseling_response import log_counseling_response, start_counseling_mode
    from src.services.sage_bot_response import build_counseling_bot

    text = (user_message or "").strip()
    if text and not was_last_user_message(session, text):
        append_user_message(session, text)

    from src.utils.user_attribute_registration import append_user_attribute_registration_notice

    append_user_attribute_registration_notice(session, sid)

    response_text = build_allergy_entry_response(text)
    start_counseling_mode(session, "allergy", _ALLERGY_INITIAL_QUESTIONS)

    bot_response = build_counseling_bot(
        session,
        sid,
        response_text,
        title="カウンセリング",
        kind="counseling_allergy_entry",
        counseling=True,
        uuid=str(uuid.uuid4()),
    )
    session.setdefault("messages", []).append(bot_response)
    if hasattr(session, "modified"):
        session.modified = True

    if sid:
        session_data = get_session_from_db(sid) or {}
        session_data["messages"] = list(session.get("messages") or [])
        session_data["last_activity"] = datetime.now()
        session_data["user_attributes"] = session.get(
            "user_attributes", session_data.get("user_attributes", {})
        )
        session_data["counseling_mode"] = session.get("counseling_mode", {})
        save_session_to_db(sid, session_data)

    try:
        log_counseling_response(
            session_id=sid,
            response_content=response_text,
            response_type="counseling_allergy_entry",
            category="Physical",
            confidence=0.9,
            counseling_mode=session.get("counseling_mode"),
            user_input=user_message,
            conversation_history=None,
        )
    except Exception:
        pass

    logger.info("🌸 環境アレルギー相談入口: カウンセリング返信 sid=%s", sid)
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
