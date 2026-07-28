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
    bind_worker_stream_sink,
    deactivate_stream_sink,
    get_active_session_sink,
    get_stream_turn_message,
    is_session_stream_active,
    note_stream_turn_message,
    peek_stream_result,
    pop_stream_result,
    replay_session_events,
    set_stream_result,
)
from src.services.chat_inflight import (
    end_chat_job,
    is_chat_job_in_flight,
    should_orphan_persist,
)
from src.utils.chat_http_context import ChatClientInfo

logger = logging.getLogger(__name__)

_STREAM_TIMEOUT_SEC = float(os.getenv("CHAT_STREAM_TIMEOUT_SEC", "120"))
_QUEUE_WAIT_SEC = float(os.getenv("CHAT_STREAM_QUEUE_WAIT_SEC", "120"))
_KEEPALIVE_SEC = float(os.getenv("CHAT_STREAM_KEEPALIVE_SEC", "10"))
_ORPHAN_MAX_SEC = float(os.getenv("CHAT_STREAM_ORPHAN_MAX_SEC", "120"))
_sid_stream_async_locks: Dict[str, asyncio.Lock] = {}


def _sid_async_stream_lock(sid: str) -> asyncio.Lock:
    lk = _sid_stream_async_locks.get(sid)
    if lk is None:
        lk = asyncio.Lock()
        _sid_stream_async_locks[sid] = lk
    return lk
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
            for flag in (
                "detected_language",
                "language",
                "medical_emergency_otc_locked",
                "crisis_detected",
                "emergency_detected",
                "concierge_state",
                "counseling_mode",
                "last_triage_result",
                "_last_triage_result",
                "pending_memory_delete",
                "dialogue_state",
                "clarification_text_counts",
                "_fever_context_active",
                "_pipeline_end_guard",
            ):
                if flag in session_data:
                    safe_session[flag] = session_data[flag]


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
    worker_timing: Optional[Dict[str, Any]] = None,
) -> tuple:
    """SSE ワーカー内では sync pipeline を直接実行（同一 ThreadPool への二重 submit を避ける）。"""
    from src.utils.session_sid import bind_request_session_sid

    if worker_timing is not None:
        worker_timing["started"] = True
        worker_timing["started_at"] = time.monotonic()
    bind_request_session_sid(safe_session, sid)
    if worker_timing and worker_timing.get("job_token"):
        from src.services.chat_inflight import bind_job_token

        bind_job_token(worker_timing["job_token"])
    inflight_reserved = bool(worker_timing and worker_timing.get("job_token"))
    try:
        bind_worker_stream_sink(sid)
        body, status_code = handle_chat_post(
            safe_session,
            client_info,
            message,
            sid,
            monitor,
            job_meta=worker_timing,
            inflight_reserved=inflight_reserved,
        )
        return body, status_code
    finally:
        deactivate_stream_sink(None)


async def _finalize_orphan_worker(
    worker: asyncio.Future,
    sid: str,
    safe_session: RequestSafeSession,
    request: Request,
    *,
    orphan_token: Optional[str] = None,
) -> None:
    """SSE 切断後もワーカーが完了したら DB 保存・再接続用結果を残す。"""
    try:
        body, status_code = await asyncio.wait_for(worker, timeout=_ORPHAN_MAX_SEC)
        if sid:
            set_stream_result(sid, body, status_code)
            if should_orphan_persist(sid, orphan_token):
                try:
                    persist_session_from_chat_state(sid, safe_session, request)
                except Exception:
                    logger.exception("SSE orphan worker persist failed sid=%s", sid)
            else:
                logger.warning(
                    "SSE orphan persist skipped (stale job) sid=%s orphan_token=%s",
                    sid,
                    orphan_token,
                )
    except asyncio.TimeoutError:
        logger.error(
            "SSE orphan worker exceeded %.0fs sid=%s",
            _ORPHAN_MAX_SEC,
            sid,
        )
    except Exception:
        logger.exception("SSE orphan worker failed sid=%s", sid)
    finally:
        if sid:
            from src.services.processing_status import clear_processing_status

            clear_processing_status(sid)


def _stream_elapsed_sec(
    started_at: float,
    worker_timing: Dict[str, Any],
) -> tuple[float, bool]:
    """経過秒と、処理タイムアウト判定対象か（ワーカー開始後）を返す。"""
    if worker_timing.get("started") and worker_timing.get("started_at") is not None:
        return time.monotonic() - float(worker_timing["started_at"]), True
    return time.monotonic() - started_at, False


def _yield_sink_events(sink: StreamSink) -> tuple[list[str], bool]:
    lines: list[str] = []
    got_done = False
    for event, data, eid in sink.drain_nowait():
        lines.append(_sse_line(event, data, event_id=eid))
        if event == "done":
            got_done = True
    return lines, got_done


def _last_event_id_from_request(request: Request) -> Optional[str]:
    return request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")


def _messages_for_sse_done(
    session: Any,
    sid: Optional[str],
    body: Any,
) -> list:
    """SSE done 用メッセージ。in-memory が空でも DB に保存済みなら DB から復元。"""
    messages = list(session.get("messages") or []) if session is not None else []
    if messages:
        return messages
    if not sid or not isinstance(body, dict):
        return messages
    if int(body.get("message_count") or 0) <= 0:
        return messages
    session_data = get_session_from_db(sid) or {}
    return list(session_data.get("messages") or [])


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


def _build_sse_done_event(
    body: Any,
    status_code: int,
    messages: list,
    *,
    sid: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> "SseDoneEvent":
    from src.handlers.sse_events import SseDoneEvent

    duplicate_skip = bool(isinstance(body, dict) and body.get("duplicate_skip"))
    bot_message, user_message = _extract_done_messages(messages)
    if duplicate_skip:
        bot_message = None
        if messages and isinstance(messages[-1], dict) and messages[-1].get("type") == "user":
            user_message = messages[-1]

    body_dict = body if isinstance(body, dict) else {}
    return SseDoneEvent(
        http_status=status_code,
        status=body_dict.get("status", "ok"),
        message_count=body_dict.get("message_count", 0),
        session_id=sid,
        trace_id=trace_id,
        bot_message=bot_message,
        user_message=user_message,
        diagnosis=(bot_message or {}).get("diagnosis") if bot_message else None,
        duplicate_skip=duplicate_skip,
        error=bool(body_dict.get("error")),
        warning=bool(body_dict.get("warning")),
        response=body_dict.get("response"),
        risk_score=body_dict.get("risk_score"),
        dev_preview_kind=body_dict.get("dev_preview_kind"),
    )


def _build_done_lines(
    body: Any,
    status_code: int,
    safe_session: RequestSafeSession,
    sid: str,
    *,
    trace_id: Optional[str] = None,
    reattach: bool = False,
    sink: Optional[StreamSink] = None,
) -> list[str]:
    """done (+ 必要なら client_preview) の SSE 行リスト。sink 指定時は reattach クライアント向けにも emit。"""
    messages = _messages_for_sse_done(safe_session, sid, body)
    done = _build_sse_done_event(body, status_code, messages, sid=sid, trace_id=trace_id)
    payload = done.to_payload()
    from src.dialogue.adapters.web_sse import merge_dialogue_delivery_into_done

    payload = merge_dialogue_delivery_into_done(payload, safe_session, sid)
    lines: list[str] = []
    if done.error or done.warning:
        preview_payload = {
            "error": done.error,
            "warning": done.warning,
            "response": done.response,
            "message_count": done.message_count,
            "dev_preview_kind": done.dev_preview_kind,
        }
        if done.risk_score is not None:
            preview_payload["risk_score"] = done.risk_score
        if sink and not sink._closed:
            sink.emit("client_preview", preview_payload, event_id="client_preview")
        lines.append(_sse_line("client_preview", preview_payload, event_id="client_preview"))
    if reattach:
        payload["reattach"] = True
    if sink and not sink._closed:
        sink.emit("done", payload, event_id="done")
    lines.append(_sse_line("done", payload, event_id="done"))
    return lines


def build_stream_done_payload(
    body: Any,
    status_code: int,
    safe_session: RequestSafeSession,
    sid: str,
    *,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """GET /api/chat/stream-result 用の done ペイロード。"""
    messages = _messages_for_sse_done(safe_session, sid, body)
    done = _build_sse_done_event(body, status_code, messages, sid=sid, trace_id=trace_id)
    payload = done.to_payload()
    from src.dialogue.adapters.web_sse import merge_dialogue_delivery_into_done

    return merge_dialogue_delivery_into_done(payload, safe_session, sid)


async def stream_chat_events(
    request: Request,
    message: str,
    sid: str,
    monitor: Any,
) -> AsyncIterator[str]:
    last_event_id = _last_event_id_from_request(request)
    if sid and not last_event_id:
        async with _sid_async_stream_lock(sid):
            async for line in _stream_chat_events_unlocked(
                request, message, sid, monitor, last_event_id=last_event_id
            ):
                yield line
    else:
        async for line in _stream_chat_events_unlocked(
            request, message, sid, monitor, last_event_id=last_event_id
        ):
            yield line


async def _stream_chat_events_unlocked(
    request: Request,
    message: str,
    sid: str,
    monitor: Any,
    *,
    last_event_id: Optional[str],
) -> AsyncIterator[str]:
    client_info = ChatClientInfo.from_starlette_request(request)
    from src.services.processing_status import (
        clear_processing_status,
        mark_processing_step,
        status_sse_payload_for_session,
    )

    if sid and last_event_id:
        for event, data, eid in replay_session_events(sid, last_event_id):
            yield _sse_line(event, data, event_id=eid)

    safe_session = RequestSafeSession()
    _prime_safe_session_for_chat(safe_session, sid, request)

    # 新規ターン開始時の stale cache 破棄は reserve 成功後（ワーカー所有者のみ）に行う。
    # ここで pop すると reattach / stream-result 回復用の結果を duplicate POST が消してしまう。

    turn_text = message.strip()
    logger.info(
        "SSE stream begin sid=%s inflight=%s active_sink=%s last_event_id=%s",
        sid,
        is_chat_job_in_flight(sid),
        is_session_stream_active(sid),
        last_event_id,
    )
    if sid and turn_text and not last_event_id:
        if not is_chat_job_in_flight(sid):
            turn_msg = get_stream_turn_message(sid)
            pending_stale = peek_stream_result(sid)
            if pending_stale and (not turn_msg or turn_msg != turn_text):
                pop_stream_result(sid)

    cached_early = peek_stream_result(sid) if sid else None
    if cached_early and last_event_id:
        body, status_code = pop_stream_result(sid)
        if body is not None:
            for line in _build_done_lines(body, status_code, safe_session, sid, reattach=True):
                yield line
            return

    if sid and last_event_id and is_chat_job_in_flight(sid):
        wait_started = time.monotonic()
        while True:
            cached = pop_stream_result(sid)
            if cached:
                body, status_code = cached
                for line in _build_done_lines(body, status_code, safe_session, sid, reattach=True):
                    yield line
                return
            if not is_chat_job_in_flight(sid):
                break
            if time.monotonic() - wait_started > _STREAM_TIMEOUT_SEC:
                yield _sse_line(
                    "error",
                    {
                        "code": "stream_timeout",
                        "message": "処理に時間がかかりすぎています。回答の取得を続けています…",
                        "recoverable": True,
                        "fallback_hint": "POST /",
                    },
                    event_id="error",
                )
                return
            await asyncio.sleep(0.25)

    sink: Optional[StreamSink] = None
    reattach = False
    worker: Optional[asyncio.Future] = None
    owns_worker = False
    worker_timing: Dict[str, Any] = {"started": False, "started_at": None, "job_token": None}
    early_done_lines: list[str] = []
    replay_lines: list[str] = []

    if sid:
        active_sink = get_active_session_sink(sid)
        if is_chat_job_in_flight(sid):
            reattach = True
            if active_sink and not active_sink._closed:
                sink = active_sink
        else:
            sink, reattach = activate_stream_sink(sid)

        if not reattach:
            from src.services.chat_inflight import bind_job_token, reserve_chat_job

            pending = peek_stream_result(sid)
            if pending and not is_chat_job_in_flight(sid):
                turn_msg = get_stream_turn_message(sid)
                if turn_msg and turn_msg == turn_text:
                    body, status_code = pop_stream_result(sid)
                    if body is not None:
                        early_done_lines = _build_done_lines(
                            body, status_code, safe_session, sid, reattach=True
                        )

            if not early_done_lines:
                stream_reserved_token = reserve_chat_job(sid)
                if stream_reserved_token is None:
                    logger.info("SSE stream reattach (chat job in flight) sid=%s", sid)
                    reattach = True
                    sink = get_active_session_sink(sid) or sink
                else:
                    logger.info("SSE stream reserved sid=%s token=%s", sid, stream_reserved_token[:8])
                    pop_stream_result(sid)
                    note_stream_turn_message(sid, turn_text)
                    worker_timing["job_token"] = stream_reserved_token
                    bind_job_token(stream_reserved_token)
                    owns_worker = True
                    loop = asyncio.get_running_loop()
                    from src.services.chat_worker import get_chat_executor

                    worker = loop.run_in_executor(
                        get_chat_executor(),
                        _run_chat_post,
                        safe_session,
                        client_info,
                        message,
                        sid,
                        monitor,
                        worker_timing,
                    )
        elif reattach:
            sink = get_active_session_sink(sid) or sink

        if reattach and not last_event_id:
            for event, data, eid in replay_session_events(sid, None):
                replay_lines.append(_sse_line(event, data, event_id=eid))
    elif not sid:
        owns_worker = True
        loop = asyncio.get_running_loop()
        from src.services.chat_worker import get_chat_executor

        worker = loop.run_in_executor(
            get_chat_executor(),
            _run_chat_post,
            safe_session,
            client_info,
            message,
            sid,
            monitor,
            worker_timing,
        )

    if early_done_lines:
        for line in early_done_lines:
            yield line
        return

    for line in replay_lines:
        yield line

    if sid and not last_event_id and not reattach:
        mark_processing_step(sid, "validate")
        yield _sse_line("status", status_sse_payload_for_session(sid), event_id="1")

    started_at = time.monotonic()
    last_keepalive = started_at
    try:
        while True:
            if reattach and sid:
                peeked = peek_stream_result(sid)
                if peeked:
                    turn_msg = get_stream_turn_message(sid)
                    if turn_msg and turn_msg == turn_text:
                        body, status_code = pop_stream_result(sid)
                        if body is not None:
                            for line in _build_done_lines(
                                body, status_code, safe_session, sid, reattach=True
                            ):
                                yield line
                            return

            if sink:
                lines, got_done = _yield_sink_events(sink)
                for line in lines:
                    yield line
                if reattach and got_done:
                    return

            now = time.monotonic()
            if now - last_keepalive >= _KEEPALIVE_SEC:
                yield ": keepalive\n\n"
                last_keepalive = now

            if owns_worker and worker and worker.done():
                break
            if owns_worker and worker:
                elapsed, worker_started = _stream_elapsed_sec(started_at, worker_timing)
                if worker_started and elapsed > _STREAM_TIMEOUT_SEC:
                    logger.error(
                        "SSE chat worker timeout after %.0fs sid=%s",
                        _STREAM_TIMEOUT_SEC,
                        sid,
                    )
                    yield _sse_line(
                        "error",
                        {
                            "code": "stream_timeout",
                            "message": "処理に時間がかかりすぎています。回答の取得を続けています…",
                            "recoverable": True,
                            "fallback_hint": "POST /",
                        },
                        event_id="error",
                    )
                    break
                if not worker_started and elapsed > _QUEUE_WAIT_SEC:
                    logger.error(
                        "SSE chat worker queue wait timeout after %.0fs sid=%s",
                        _QUEUE_WAIT_SEC,
                        sid,
                    )
                    yield _sse_line(
                        "error",
                        {
                            "code": "worker_queue_timeout",
                            "message": "混雑のため処理開始に時間がかかっています。しばらくしてからもう一度お試しください。",
                            "recoverable": True,
                            "fallback_hint": "POST /",
                        },
                        event_id="error",
                    )
                    break
            if reattach and sid and not is_session_stream_active(sid):
                turn_msg = get_stream_turn_message(sid)
                if turn_msg and turn_msg == turn_text:
                    cached = pop_stream_result(sid)
                    if cached:
                        body, status_code = cached
                        for line in _build_done_lines(
                            body, status_code, safe_session, sid, reattach=True
                        ):
                            yield line
                        return
                if is_chat_job_in_flight(sid):
                    if time.monotonic() - started_at > _STREAM_TIMEOUT_SEC:
                        yield _sse_line(
                            "error",
                            {
                                "code": "stream_timeout",
                                "message": "処理に時間がかかりすぎています。回答の取得を続けています…",
                                "recoverable": True,
                                "fallback_hint": "POST /",
                            },
                            event_id="error",
                        )
                        return
                else:
                    peeked = peek_stream_result(sid)
                    if peeked and turn_msg and turn_msg == turn_text:
                        body, status_code = pop_stream_result(sid)
                        if body is not None:
                            for line in _build_done_lines(
                                body, status_code, safe_session, sid, reattach=True
                            ):
                                yield line
                            return
                    if time.monotonic() - started_at > _STREAM_TIMEOUT_SEC:
                        logger.warning(
                            "SSE reattach ended without result sid=%s",
                            sid,
                        )
                        return
            await asyncio.sleep(0.02)

        if sink:
            lines, _ = _yield_sink_events(sink)
            for line in lines:
                yield line

        if owns_worker and worker and worker.done():
            body, status_code = await worker
            if sid:
                set_stream_result(sid, body, status_code)
                note_stream_turn_message(sid, message.strip())
                try:
                    persist_session_from_chat_state(sid, safe_session, request)
                except Exception:
                    logger.exception("SSE persist before done failed sid=%s", sid)
            trace_id = safe_session.get("last_trace_id")
            for line in _build_done_lines(
                body,
                status_code,
                safe_session,
                sid,
                trace_id=trace_id,
                sink=sink,
            ):
                yield line
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
        worker_still_running = owns_worker and worker is not None and not worker.done()
        if sink and owns_worker:
            sink.close()
        if sid and owns_worker:
            deactivate_stream_sink(sid)
        elif not owns_worker:
            deactivate_stream_sink(None)
        if worker_still_running:
            asyncio.create_task(
                _finalize_orphan_worker(
                    worker,
                    sid,
                    safe_session,
                    request,
                    orphan_token=worker_timing.get("job_token"),
                )
            )
        elif sid and owns_worker:
            try:
                persist_session_from_chat_state(sid, safe_session, request)
            except Exception:
                pass
            clear_processing_status(sid)
