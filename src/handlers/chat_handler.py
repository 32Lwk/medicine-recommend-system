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
    return run_chat_post_pipeline(session, client_info, message, sid, monitor)
