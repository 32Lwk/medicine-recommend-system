"""LINE イベント時刻の timestamp 反映テスト。"""
from __future__ import annotations

from datetime import datetime

from src.handlers.line.line_progressive_delivery import LineDeliveryContext, set_line_delivery_context
from src.handlers.line.line_timestamp import (
    line_event_ms_to_iso,
    line_event_timestamp_ms,
    resolve_inbound_message_timestamp,
)
from src.services.session_manager import append_user_message
from src.utils.jst_datetime import JST


def _jst_ms(y, m, d, h, mi, s) -> int:
    dt = datetime(y, m, d, h, mi, s, tzinfo=JST)
    return int(dt.timestamp() * 1000)


def test_line_event_ms_to_iso():
    ms = _jst_ms(2026, 6, 22, 7, 7, 41)
    iso = line_event_ms_to_iso(ms)
    assert iso == "2026-06-22T07:07:41+09:00"


def test_line_event_timestamp_ms_from_event():
    assert line_event_timestamp_ms({"timestamp": 1718982461000}) == 1718982461000
    assert line_event_timestamp_ms({"timestamp": "bad"}) is None


def test_resolve_inbound_message_timestamp_uses_line_context():
    ms = _jst_ms(2026, 6, 22, 6, 10, 9)
    ctx = LineDeliveryContext(
        user_id="Utest",
        reply_token=None,
        lang="ja",
        sid="line:Utest",
        event_timestamp_ms=ms,
    )
    set_line_delivery_context(ctx)
    try:
        iso = resolve_inbound_message_timestamp()
        assert iso == "2026-06-22T06:10:09+09:00"
    finally:
        set_line_delivery_context(None)


def test_append_user_message_uses_line_event_timestamp_for_line_session():
    ms = _jst_ms(2026, 6, 22, 6, 10, 9)
    ctx = LineDeliveryContext(
        user_id="Ulineuser",
        reply_token=None,
        lang="ja",
        sid="line:Ulineuser",
        event_timestamp_ms=ms,
    )
    session = {"_id": "line:Ulineuser", "messages": []}
    set_line_delivery_context(ctx)
    try:
        msg = append_user_message(session, "こんにちは")
        assert msg["timestamp"] == "2026-06-22T06:10:09+09:00"
    finally:
        set_line_delivery_context(None)


def test_append_user_message_web_session_uses_server_now():
    session = {"_id": "1234567890", "messages": []}
    msg = append_user_message(session, "hello")
    assert "+09:00" in msg["timestamp"]
