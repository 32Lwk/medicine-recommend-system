"""SSE イベントバス"""
from src.services.sse_emit import (
    StreamSink,
    activate_stream_sink,
    deactivate_stream_sink,
    emit_advice_delta,
    emit_cards,
    get_stream_sink,
    is_streaming_active,
    pseudo_stream_advice,
    replay_session_events,
)


def test_stream_sink_emit_and_drain():
    sink = StreamSink("sess-1")
    sink.emit("advice_delta", {"text": "あ"})
    sink.emit("cards", {"medicines": [], "count": 0})
    drained = sink.drain_nowait()
    assert len(drained) == 2
    assert drained[0][0] == "advice_delta"
    assert drained[1][0] == "cards"


def test_activate_emit_advice_preview():
    sink, reattach = activate_stream_sink("sess-2")
    assert reattach is False
    try:
        assert get_stream_sink() is sink
        assert is_streaming_active("sess-2")
        emit_advice_delta("hello", "sess-2")
        events = sink.drain_nowait()
        assert events[0][1]["text"] == "hello"
    finally:
        deactivate_stream_sink("sess-2")
    assert get_stream_sink() is None


def test_replay_session_events_after_id():
    sink, _ = activate_stream_sink("replay-s")
    try:
        emit_advice_delta("a", "replay-s")
        emit_advice_delta("b", "replay-s")
        events = sink.drain_nowait()
        first_id = events[0][2]
        replayed = replay_session_events("replay-s", first_id)
        assert len(replayed) == 1
        assert replayed[0][1]["text"] == "b"
    finally:
        deactivate_stream_sink("replay-s")


def test_emit_cards_payload():
    sink, _ = activate_stream_sink("s")
    try:
        emit_cards(
            [{"product_name": "薬A", "manufacturer": "社A", "efficacy": "風邪"},
             {"name": "薬B"}],
            session_id="s",
        )
        ev = sink.drain_nowait()[0]
        assert ev[0] == "cards"
        assert ev[1]["count"] == 2
        assert ev[1]["medicines"][0]["product_name"] == "薬A"
        assert ev[1]["medicines"][0]["manufacturer"] == "社A"
    finally:
        deactivate_stream_sink("s")


def test_pseudo_stream_noop_without_sink():
    pseudo_stream_advice("text", "no-sink")
