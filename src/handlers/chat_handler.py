"""
チャットPOSTリクエストハンドラー

index() の POST 処理を chat_post_pipeline に委譲する薄型エントリポイント。
"""
from __future__ import annotations

import logging

from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline, run_chat_post_pipeline_async
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)


async def handle_chat_post_async(session, client_info: ChatClientInfo, message: str, sid, monitor):
    """
    チャット POST を非同期エントリで処理（パイプライン本体はワーカースレッド）。

    Returns:
        tuple[dict, int]: JSON 本文と HTTP ステータス
    """
    from src.handlers.line.line_session import is_line_session_id
    from src.services.chat_inflight import end_chat_job, try_begin_chat_job
    from src.services.pipeline_perf import ensure_pipeline_perf_started, log_pipeline_perf

    channel = "line" if sid and is_line_session_id(sid) else "web"
    ensure_pipeline_perf_started(channel=channel)
    is_line_channel = channel == "line"

    if not try_begin_chat_job(sid):
        logger.warning("Skipping duplicate chat POST sid=%s", sid)
        count = len(session.get("messages") or []) if session else 0
        return ({"status": "ok", "message_count": count}, 200)
    try:
        return await run_chat_post_pipeline_async(
            session,
            client_info,
            message,
            sid,
            monitor,
        )
    finally:
        end_chat_job(sid)
        if not is_line_channel:
            log_pipeline_perf(sid=sid)


def handle_chat_post(session, client_info: ChatClientInfo, message: str, sid, monitor):
    """
    チャットPOSTリクエストを処理する（Flask 等 sync ルート向け）。

    Returns:
        tuple[dict, int]: JSON 本文と HTTP ステータス
    """
    from src.handlers.line.line_session import is_line_session_id
    from src.services.chat_inflight import end_chat_job, try_begin_chat_job
    from src.services.pipeline_perf import ensure_pipeline_perf_started, log_pipeline_perf

    channel = "line" if sid and is_line_session_id(sid) else "web"
    ensure_pipeline_perf_started(channel=channel)
    is_line_channel = channel == "line"

    if not try_begin_chat_job(sid):
        logger.warning("Skipping duplicate chat POST sid=%s", sid)
        count = len(session.get("messages") or []) if session else 0
        return ({"status": "ok", "message_count": count}, 200)
    try:
        return run_chat_post_pipeline(session, client_info, message, sid, monitor)
    finally:
        end_chat_job(sid)
        if not is_line_channel:
            log_pipeline_perf(sid=sid)
