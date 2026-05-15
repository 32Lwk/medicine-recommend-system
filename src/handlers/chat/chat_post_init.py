"""
POST 初期処理（空メッセージ・追加情報モーダルプレフィックス）
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]
ADDITIONAL_INFO_PREFIX = "[ADDITIONAL_INFO_SUBMIT]"


def parse_incoming_message(session: Any, message: str) -> str:
    user_message = (message or "").strip()
    if user_message.startswith(ADDITIONAL_INFO_PREFIX):
        user_message = user_message[len(ADDITIONAL_INFO_PREFIX) :].strip()
        session["from_attribute_modal"] = True
        logger.info("📋 追加情報モーダルからの送信を検知")
    else:
        session["from_attribute_modal"] = False
    logger.info("📝 受信メッセージ: %s", user_message)
    return user_message


def empty_message_response(
    session: Any,
    sid: Optional[str],
    monitor: Any,
    user_agent: str,
    client_ip: str,
) -> Optional[ResponseTuple]:
    """空メッセージ時の早期 return（ログ付き）"""
    message_count = len(session.get("messages", []))
    try:
        from src.utils.performance_monitor import log_performance_metrics
        from src.services.analytics import log_access_analytics

        metrics = monitor.get_metrics()
        log_performance_metrics(monitor, sid, "POST_request", {
            "user_agent": user_agent,
            "client_ip": client_ip,
        })
        from src.services.session_manager import get_session_from_db

        session_data = get_session_from_db(sid) if sid else None
        actual_message_count = (
            len(session_data.get("messages", [])) if session_data else message_count
        )
        log_access_analytics(sid, user_agent, client_ip, metrics["response_time_ms"], {
            "username": session.get("username", ""),
            "message_count": actual_message_count,
        })
    except Exception as e:
        logger.warning("ログ出力エラー（無視）: %s", e)
    return ({"status": "ok", "message_count": message_count}, 200)
