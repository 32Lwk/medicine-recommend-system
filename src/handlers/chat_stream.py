"""
チャット SSE ストリーム

handle_chat_post をワーカースレッドで実行しつつ、
LLM からの advice_delta / cards をリアルタイム配信する。
Last-Event-ID 再接続時はセッションリングバッファを再生する。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, AsyncIterator, Dict, Optional

from starlette.requests import Request

from src.handlers.chat_handler import handle_chat_post_async
from src.services.session_manager import (
    get_next_user_number,
    get_session_from_db,
    persist_session_from_chat_state,
)
from src.utils.request_safe_session import RequestSafeSession
from src.services.sse_emit import (
    StreamSink,
    activate_stream_sink,
    bind_worker_stream_sink,
    deactivate_stream_sink,
    get_active_session_sink,
    is_session_stream_active,
    pop_stream_result,
    replay_session_events,
    set_stream_result,
)
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)

_STREAM_TIMEOUT_SEC = float(os.getenv("CHAT_STREAM_TIMEOUT_SEC", "180"))
_KEEPALIVE_SEC = float(os.getenv("CHAT_STREAM_KEEPALIVE_SEC", "10"))
def _prime_safe_session_for_chat(safe_session: RequestSafeSession, sid: str, request: Any = None) -> None:
    from config.ui_config import UI_VARIANT_COOKIE, UI_VARIANT_QUERY, resolve_ui_variant

    safe_session.setdefault("messages", [])
    safe_session.setdefault(
        "user_attributes",
        {
            "age": None,
            "gender": None,
            "pregnant": None,
            "breastfeeding": None,
            "current_medications": [],
            "allergies": [],
            "medical_history": [],
            "symptom_duration_days": None,
            "other_info": None,
        },
    )
    if sid:
        safe_session["_id"] = sid
    if request is not None:
        query_ui = getattr(request, "query_params", {}).get(UI_VARIANT_QUERY) if hasattr(request, "query_params") else None
        cookie_ui = request.cookies.get(UI_VARIANT_COOKIE) if hasattr(request, "cookies") else None
        safe_session["ui_variant"] = resolve_ui_variant(query_ui=query_ui, cookie_ui=cookie_ui)
    if "username" not in safe_session:
        safe_session["username"] = f"ユーザー{get_next_user_number()}"
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            safe_session["messages"] = (session_data.get("messages") or []).copy()
            db_attrs = session_data.get("user_attributes") or {}
            if db_attrs:
                current_attrs = safe_session.get("user_attributes", {}) or {}
                safe_session["user_attributes"] = {**current_attrs, **db_attrs}


def _sse_line(event: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _run_chat_post(
    safe_session: RequestSafeSession,
    client_info: ChatClientInfo,
    message: str,
    sid: str,
    monitor: Any,
) -> tuple:
    bind_worker_stream_sink(sid)
    return asyncio.run(
        handle_chat_post_async(safe_session, client_info, message, sid, monitor)
    )


def _yield_sink_events(sink: StreamSink) -> list[str]:
    lines: list[str] = []
    for event, data, eid in sink.drain_nowait():
        lines.append(_sse_line(event, data, event_id=eid))
    return lines


def _last_event_id_from_request(request: Request) -> Optional[str]:
    return request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")


def _extract_done_messages(messages: list) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """末尾が user でも、直近の bot とその直前 user を done ペイロード用に返す。"""
    if not messages:
        return None, None
    bot_message: Optional[Dict[str, Any]] = None
    user_message: Optional[Dict[str, Any]] = None
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        if bot_message is None and msg.get("type") == "bot":
            bot_message = msg
            continue
        if bot_message is not None and msg.get("type") == "user":
            user_message = msg
            break
    return bot_message, user_message


async def stream_chat_events(
    request: Request,
    message: str,
    sid: str,
    monitor: Any,
) -> AsyncIterator[str]:
    client_info = ChatClientInfo.from_starlette_request(request)
    from src.services.processing_status import (
        clear_processing_status,
        mark_processing_step,
        status_sse_payload_for_session,
    )

    last_event_id = _last_event_id_from_request(request)

    if sid and last_event_id:
        for event, data, eid in replay_session_events(sid, last_event_id):
            yield _sse_line(event, data, event_id=eid)

    safe_session = RequestSafeSession()
    _prime_safe_session_for_chat(safe_session, sid, request)

    sink: Optional[StreamSink] = None
    reattach = False
    if sid:
        sink, reattach = activate_stream_sink(sid, allow_reattach=bool(last_event_id))
    elif not sid:
        pass

    if sid and not last_event_id:
        mark_processing_step(sid, "validate")
        yield _sse_line("status", status_sse_payload_for_session(sid), event_id="1")

    worker: Optional[asyncio.Future] = None
    owns_worker = False

    if reattach:
        sink = get_active_session_sink(sid) or sink
    else:
        owns_worker = True
        loop = asyncio.get_running_loop()
        from src.services.chat_worker import get_chat_executor

        # run_in_executor は await 可能な Future を返す（create_task 不可）
        worker = loop.run_in_executor(
            get_chat_executor(),
            _run_chat_post,
            safe_session,
            client_info,
            message,
            sid,
            monitor,
        )

    started_at = time.monotonic()
    last_keepalive = started_at
    try:
        while True:
            if sink:
                for line in _yield_sink_events(sink):
                    yield line

            now = time.monotonic()
            if now - last_keepalive >= _KEEPALIVE_SEC:
                yield ": keepalive\n\n"
                last_keepalive = now

            if owns_worker and worker and worker.done():
                break
            if owns_worker and worker and (time.monotonic() - started_at) > _STREAM_TIMEOUT_SEC:
                logger.error("SSE chat worker timeout after %.0fs sid=%s", _STREAM_TIMEOUT_SEC, sid)
                yield _sse_line(
                    "error",
                    {
                        "code": "stream_timeout",
                        "message": "処理に時間がかかりすぎています。もう一度お試しください。",
                        "fallback_hint": "POST /",
                    },
                    event_id="error",
                )
                break
            if reattach and sid and not is_session_stream_active(sid):
                cached = pop_stream_result(sid)
                if cached:
                    body, status_code = cached
                    from src.handlers.sse_events import SseDoneEvent

                    bot_message = None
                    user_message = None
                    session_data = get_session_from_db(sid) or {}
                    messages = list(session_data.get("messages") or [])
                    bot_message, user_message = _extract_done_messages(messages)
                    done = SseDoneEvent(
                        http_status=status_code,
                        status=body.get("status", "ok") if isinstance(body, dict) else "ok",
                        message_count=body.get("message_count", 0) if isinstance(body, dict) else 0,
                        bot_message=bot_message,
                        user_message=user_message,
                    )
                    payload = done.to_payload()
                    payload["reattach"] = True
                    yield _sse_line("done", payload, event_id="done")
                return
            await asyncio.sleep(0.02)

        if sink:
            for line in _yield_sink_events(sink):
                yield line

        if owns_worker and worker and worker.done():
            body, status_code = await worker
            if sid:
                set_stream_result(sid, body, status_code)
                try:
                    persist_session_from_chat_state(sid, safe_session, request)
                except Exception:
                    logger.exception("SSE persist before done failed sid=%s", sid)
            from src.handlers.sse_events import SseDoneEvent

            trace_id = safe_session.get("last_trace_id")
            messages = list(safe_session.get("messages") or [])
            bot_message, user_message = _extract_done_messages(messages)
            done = SseDoneEvent(
                http_status=status_code,
                status=body.get("status", "ok") if isinstance(body, dict) else "ok",
                message_count=body.get("message_count", 0) if isinstance(body, dict) else 0,
                trace_id=trace_id,
                bot_message=bot_message,
                user_message=user_message,
            )
            yield _sse_line("done", done.to_payload(), event_id="done")
        elif owns_worker and worker and not worker.done():
            logger.warning("SSE stream ended before worker completed sid=%s", sid)

    except Exception as e:
        logger.exception("SSE stream failed: %s", e)
        yield _sse_line(
            "error",
            {"code": "stream_failed", "message": str(e), "fallback_hint": "POST /"},
            event_id="error",
        )
    finally:
        if sink and owns_worker:
            sink.close()
        if sid and owns_worker:
            deactivate_stream_sink(sid)
        elif not owns_worker:
            deactivate_stream_sink(None)
        if sid and owns_worker:
            try:
                persist_session_from_chat_state(sid, safe_session, request)
            except Exception:
                pass
            clear_processing_status(sid)
