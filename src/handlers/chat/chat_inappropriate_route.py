"""
不適切メッセージ検出とカウンセリング応答（ステップ1.7.5）
"""
from __future__ import annotations

import logging
import re
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.services.session_manager import get_next_user_number, get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

AMBIGUOUS_KEYWORDS = [
    "やばい", "ヤバい", "草", "くさ", "クサ", "H", "h",
    "尊い", "たっふい", "タッフイ", "ワロタ", "わろた",
]
NUMERIC_SLANG = ["69", "88", "419"]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def detect_inappropriate_message(normalized_message: str) -> bool:
    from config.keywords import INAPPROPRIATE_MESSAGE_KEYWORDS
    from src.services.counseling_response import normalize_text

    for num_slang in NUMERIC_SLANG:
        pattern = r"(?:^|[^\d])" + re.escape(num_slang) + r"(?:[^\d]|$)"
        if re.search(pattern, normalized_message):
            logger.warning("⚠️ 不適切なメッセージを検出（数字隠語）: %s", num_slang)
            return True

    for keyword in INAPPROPRIATE_MESSAGE_KEYWORDS:
        normalized_keyword = normalize_text(keyword)
        if len(keyword) <= 3 or keyword in AMBIGUOUS_KEYWORDS:
            pattern = r"\b" + re.escape(normalized_keyword) + r"\b"
            if re.search(pattern, normalized_message):
                logger.warning("⚠️ 不適切なメッセージを検出: %s", keyword)
                return True
        elif normalized_keyword in normalized_message:
            logger.warning("⚠️ 不適切なメッセージを検出: %s", keyword)
            return True
    return False


def handle_inappropriate_message_if_detected(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
) -> Optional[ResponseTuple]:
    """不適切メッセージ検出時はカウンセリング開始して早期 return。未検出は None。"""
    try:
        from src.services.counseling_response import (
            generate_counseling_response,
            generate_follow_up_questions,
            log_counseling_response,
            normalize_text,
            start_counseling_mode,
        )

        normalized_message = normalize_text(sanitized_message)
        if not detect_inappropriate_message(normalized_message):
            return None

        session.setdefault("messages", [])
        user_msg = {
            "type": "user",
            "content": sanitized_message,
            "timestamp": datetime.now().isoformat(),
            "uuid": str(uuid.uuid4()),
        }
        session["messages"].append(user_msg)
        _mark_session_modified(session)

        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data.setdefault("messages", []).append(user_msg)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)
            else:
                save_session_to_db(
                    sid,
                    {
                        "session_id": sid,
                        "username": session.get(
                            "username", f"ユーザー{get_next_user_number()}"
                        ),
                        "messages": [user_msg],
                        "session_active": True,
                        "last_activity": datetime.now(),
                        "client_ip": client_info.client_ip,
                        "user_agent": client_info.user_agent,
                        "user_attributes": session.get("user_attributes", {}),
                    },
                )

        symptom_type = "inappropriate_request/inappropriate_message"
        from src.services.line_memory_context import get_counseling_conversation_history

        conversation_history = get_counseling_conversation_history(session, sid)
        initial_response = generate_counseling_response(
            symptom_type,
            sanitized_message,
            recommendation_client,
            conversation_history=conversation_history,
            session_id=sid,
        )
        initial_questions = generate_follow_up_questions(symptom_type, {}, recommendation_client)
        start_counseling_mode(session, symptom_type, initial_questions)

        from src.services.sage_bot_response import build_counseling_bot

        bot_response = build_counseling_bot(
            session,
            sid,
            initial_response,
            title="カウンセリング",
            kind="counseling_inappropriate",
            counseling=True,
            inappropriate_request=True,
            request_type="inappropriate_message",
        )
        session["messages"].append(bot_response)

        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data.setdefault("messages", []).append(bot_response)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)

        log_counseling_response(
            session_id=sid,
            response_content=initial_response,
            response_type="counseling_inappropriate_message",
            category="Other",
            confidence=1.0,
            counseling_mode=session.get("counseling_mode"),
            user_input=user_message,
            conversation_history=None,
        )
        _mark_session_modified(session)
        message_count = len(session["messages"])
        logger.info("✅ 不適切なメッセージ処理完了: %s messages", message_count)
        return ({"status": "ok", "message_count": message_count}, 200)

    except ImportError as e:
        logger.warning("⚠️ 不適切なメッセージ検出機能のインポートに失敗: %s", e)
    except Exception as e:
        logger.error("❌ 不適切なメッセージ検出機能でエラー: %s", e)
        traceback.print_exc()
    return None
