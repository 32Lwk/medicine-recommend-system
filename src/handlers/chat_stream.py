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
from typing import Any, AsyncIterator, Dict, Optional

from starlette.requests import Request

from src.handlers.chat_handler import handle_chat_post
from src.services.session_manager import (
    get_next_user_number,
    get_session_from_db,
    persist_session_from_chat_state,
)
from src.utils.request_safe_session import RequestSafeSession
from src.services.sse_emit import (
    StreamSink,
    activate_stream_sink,
    deactivate_stream_sink,
    get_active_session_sink,
    is_session_stream_active,
    pop_stream_result,
    replay_session_events,
    set_stream_result,
)
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)


def _prime_safe_session_for_chat(safe_session: RequestSafeSession, sid: str) -> None:
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
    return handle_chat_post(safe_session, client_info, message, sid, monitor)


def _yield_sink_events(sink: StreamSink) -> list[str]:
    lines: list[str] = []
    for event, data, eid in sink.drain_nowait():
        lines.append(_sse_line(event, data, event_id=eid))
    return lines


def _last_event_id_from_request(request: Request) -> Optional[str]:
    return request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")


async def stream_chat_events(
    request: Request,
    message: str,
    sid: str,
    monitor: Any,
) -> AsyncIterator[str]:
    client_info = ChatClientInfo.from_starlette_request(request)
    from src.services.processing_status import clear_processing_status, mark_processing_step

    last_event_id = _last_event_id_from_request(request)

    if sid and last_event_id:
        for event, data, eid in replay_session_events(sid, last_event_id):
            yield _sse_line(event, data, event_id=eid)

    if sid:
        mark_processing_step(sid, "validate")
    yield _sse_line("status", {"step_id": "validate", "percent": 5}, event_id="1")

    safe_session = RequestSafeSession()
    _prime_safe_session_for_chat(safe_session, sid)

    sink: Optional[StreamSink] = None
    reattach = False
    if sid:
        sink, reattach = activate_stream_sink(sid)
    elif not sid:
        pass

    worker: Optional[asyncio.Task] = None
    owns_worker = False

    if reattach:
        sink = get_active_session_sink(sid) or sink
    else:
        owns_worker = True
        worker = asyncio.create_task(
            asyncio.to_thread(
                _run_chat_post,
                safe_session,
                client_info,
                message,
                sid,
                monitor,
            )
        )

    try:
        while True:
            if sink:
                for line in _yield_sink_events(sink):
                    yield line

            if owns_worker and worker and worker.done():
                break
            if reattach and sid and not is_session_stream_active(sid):
                cached = pop_stream_result(sid)
                if cached:
                    body, status_code = cached
                    payload: Dict[str, Any] = {"http_status": status_code, "reattach": True}
                    if isinstance(body, dict):
                        payload["status"] = body.get("status", "ok")
                        payload["message_count"] = body.get("message_count", 0)
                    yield _sse_line("done", payload, event_id="done")
                return
            await asyncio.sleep(0.02)

        if sink:
            for line in _yield_sink_events(sink):
                yield line

        if owns_worker and worker:
            body, status_code = await worker
            if sid:
                set_stream_result(sid, body, status_code)
            from src.handlers.sse_events import SseDoneEvent

            trace_id = None
            if isinstance(safe_session, dict):
                trace_id = safe_session.get("last_trace_id")
            done = SseDoneEvent(
                http_status=status_code,
                status=body.get("status", "ok") if isinstance(body, dict) else "ok",
                message_count=body.get("message_count", 0) if isinstance(body, dict) else 0,
                trace_id=trace_id,
            )
            yield _sse_line("done", done.to_payload(), event_id="done")

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
