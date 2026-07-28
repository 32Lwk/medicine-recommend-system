"""SSE worker sink 束縛のテスト。"""
from __future__ import annotations

from src.services.sse_emit import (
    StreamSink,
    activate_stream_sink,
    bind_worker_stream_sink,
    deactivate_stream_sink,
    get_stream_sink,
)


def test_bind_worker_stream_sink_clears_stale_contextvar():
    sink_a, _ = activate_stream_sink("session-a")
    bind_worker_stream_sink("session-a")
    assert get_stream_sink() is sink_a

    deactivate_stream_sink("session-a")
    sink_b, _ = activate_stream_sink("session-b")
    bind_worker_stream_sink("session-a")
    assert get_stream_sink() is None

    bind_worker_stream_sink("session-b")
    assert get_stream_sink() is sink_b
    deactivate_stream_sink("session-b")


def test_bind_worker_stream_sink_none_clears():
    sink, _ = activate_stream_sink("session-c")
    bind_worker_stream_sink("session-c")
    assert get_stream_sink() is sink
    bind_worker_stream_sink(None)
    assert get_stream_sink() is None
    deactivate_stream_sink("session-c")
