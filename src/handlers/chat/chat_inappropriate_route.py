"""
攻撃的・不適切メッセージ検出と境界案内応答（ステップ1.7.5）
"""
from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.session_manager import get_next_user_number, get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def detect_inappropriate_message(normalized_message: str) -> bool:
    from src.security.aggressive_input import is_non_absolute_aggressive_expression

    return is_non_absolute_aggressive_expression(normalized_message)[0]


def handle_inappropriate_message_if_detected(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: Any,
) -> Optional[ResponseTuple]:
    """攻撃的入力検出時は境界案内を返して早期 return。未検出は None。"""
    del recommendation_client
    try:
        from src.security.input_block_responses import match_input_block
        from src.services.sage_bot_response import build_notice_bot

        block_notice = match_input_block(sanitized_message)
        if not block_notice:
            return None

        logger.warning(
            "⚠️ 不適切入力を検出: category=%s reason=%s",
            block_notice.category,
            block_notice.reason,
        )

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

        bot_response = build_notice_bot(
            session,
            sid,
            block_notice.message,
            title=block_notice.title,
            variant=block_notice.variant,
            kind=block_notice.kind,
            uuid=str(uuid.uuid4()),
        )
        session["messages"].append(bot_response)

        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data.setdefault("messages", []).append(bot_response)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)

        _mark_session_modified(session)
        message_count = len(session["messages"])
        logger.info("✅ 攻撃的入力の境界案内を返却: %s messages", message_count)
        if sid:
            try:
                from src.services.processing_status import clear_processing_status

                clear_processing_status(sid)
            except ImportError:
                pass
        return (
            {
                "status": "ok",
                "message_count": message_count,
                "response": block_notice.message,
            },
            200,
        )

    except ImportError as e:
        logger.warning("⚠️ 攻撃的入力検出機能のインポートに失敗: %s", e)
    except Exception as e:
        logger.error("❌ 攻撃的入力検出機能でエラー: %s", e)
        traceback.print_exc()
    return None
