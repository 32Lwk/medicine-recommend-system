"""
チャットPOSTリクエストハンドラー

index() の POST 処理を chat_post_pipeline に委譲する薄型エントリポイント。
"""
from __future__ import annotations

import logging

from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)


def handle_chat_post(session, client_info: ChatClientInfo, message: str, sid, monitor):
    """
    チャットPOSTリクエストを処理する。

    Returns:
        tuple[dict, int]: JSON 本文と HTTP ステータス
    """
    from src.services.chat_inflight import end_chat_job, try_begin_chat_job

    if not try_begin_chat_job(sid):
        logger.warning("Skipping duplicate chat POST sid=%s", sid)
        count = len(session.get("messages") or []) if session else 0
        return ({"status": "ok", "message_count": count}, 200)
    try:
        return run_chat_post_pipeline(session, client_info, message, sid, monitor)
    finally:
        end_chat_job(sid)
