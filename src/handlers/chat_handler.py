"""
チャットPOSTリクエストハンドラー

index() の POST 処理を chat_post_pipeline に委譲する薄型エントリポイント。
"""
from __future__ import annotations

import logging

from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline, run_chat_post_pipeline_async
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)


async def handle_chat_post_async(session, client_info: ChatClientInfo, message: str, sid, monitor, job_meta=None):
    """
    チャット POST を非同期エントリで処理（パイプライン本体はワーカースレッド）。

    Returns:
        tuple[dict, int]: JSON 本文と HTTP ステータス
    """
    from src.handlers.line.line_session import is_line_session_id
    from src.services.budget_guard import reset_budget_check_cache
    from src.services.chat_inflight import end_chat_job, get_current_job_token, try_begin_chat_job
    from src.services.pipeline_perf import ensure_pipeline_perf_started, log_pipeline_perf
    from src.services.request_scope_cache import clear_request_scope_cache
    from src.utils.session_sid import bind_request_session_sid

    clear_request_scope_cache()
    bind_request_session_sid(session, sid)

    channel = "line" if sid and is_line_session_id(sid) else "web"
    ensure_pipeline_perf_started(channel=channel, sid=sid)
    is_line_channel = channel == "line"

    reset_budget_check_cache()
    if not try_begin_chat_job(sid):
        logger.warning("Skipping duplicate chat POST sid=%s", sid)
        count = len(session.get("messages") or []) if session else 0
        return ({"status": "ok", "message_count": count, "duplicate_skip": True}, 200)
    if job_meta is not None:
        job_meta["job_token"] = get_current_job_token()
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
            extra = None
            if session is not None and sid and hasattr(session, "get"):
                bound = session.get("_id")
                if bound and str(bound) != str(sid):
                    extra = {"session_sid_mismatch": True, "session_bound_id": str(bound)}
            log_pipeline_perf(sid=sid, extra=extra)


def handle_chat_post(session, client_info: ChatClientInfo, message: str, sid, monitor, job_meta=None):
    """
    チャットPOSTリクエストを処理する（Flask 等 sync ルート向け）。

    Returns:
        tuple[dict, int]: JSON 本文と HTTP ステータス
    """
    from src.handlers.line.line_session import is_line_session_id
    from src.services.budget_guard import reset_budget_check_cache
    from src.services.chat_inflight import end_chat_job, get_current_job_token, try_begin_chat_job
    from src.services.pipeline_perf import ensure_pipeline_perf_started, log_pipeline_perf
    from src.services.request_scope_cache import clear_request_scope_cache
    from src.utils.session_sid import bind_request_session_sid

    clear_request_scope_cache()
    bind_request_session_sid(session, sid)

    channel = "line" if sid and is_line_session_id(sid) else "web"
    ensure_pipeline_perf_started(channel=channel, sid=sid)
    is_line_channel = channel == "line"

    reset_budget_check_cache()
    if not try_begin_chat_job(sid):
        logger.warning("Skipping duplicate chat POST sid=%s", sid)
        count = len(session.get("messages") or []) if session else 0
        return ({"status": "ok", "message_count": count, "duplicate_skip": True}, 200)
    if job_meta is not None:
        job_meta["job_token"] = get_current_job_token()
    try:
        return run_chat_post_pipeline(session, client_info, message, sid, monitor)
    finally:
        end_chat_job(sid)
        if not is_line_channel:
            extra = None
            if session is not None and sid and hasattr(session, "get"):
                bound = session.get("_id")
                if bound and str(bound) != str(sid):
                    extra = {"session_sid_mismatch": True, "session_bound_id": str(bound)}
            log_pipeline_perf(sid=sid, extra=extra)
