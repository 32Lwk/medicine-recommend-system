"""チャット SSE / in-flight テスト間の状態を分離。"""
from __future__ import annotations

import pytest


def _reset_chat_concurrency_state() -> None:
    from src.services import chat_inflight, sse_emit

    with chat_inflight._lock:
        inflight_sids = list(chat_inflight._in_flight.keys())
        chat_inflight._in_flight.clear()
    for sid in inflight_sids:
        chat_inflight.end_chat_job(sid)

    with sse_emit._lock:
        sink_sids = list(sse_emit._active_sinks.keys())
    for sid in sink_sids:
        sse_emit.clear_session_stream_state(sid)


@pytest.fixture(autouse=True)
def isolate_chat_concurrency_state():
    _reset_chat_concurrency_state()
    yield
    _reset_chat_concurrency_state()
