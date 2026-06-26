"""line_session_timestamp_backfill のテスト。"""
from __future__ import annotations

from datetime import datetime

from src.services.line_session_timestamp_backfill import (
    backfill_message_list,
    backfill_session_data,
    fix_reply_order_timestamps,
    normalize_message_timestamp_value,
)


def test_normalize_message_timestamp_value_space_format():
    iso, changed = normalize_message_timestamp_value("2026-06-21 22:07:41")
    assert changed is True
    assert iso == "2026-06-22T07:07:41+09:00"


def test_fix_reply_order_timestamps():
    messages = [
        {"type": "user", "timestamp": "2026-06-21T22:07:41"},
        {"type": "bot", "timestamp": "2026-06-21T22:07:41"},
    ]
    fixed = fix_reply_order_timestamps(messages)
    assert fixed == 1
    assert messages[1]["timestamp"] > messages[0]["timestamp"]


def test_backfill_session_data_syncs_last_activity():
    info = {
        "session_id": "line:Utest",
        "last_activity": datetime(2026, 6, 21, 19, 0, 0),
        "messages": [{"type": "user", "content": "a", "timestamp": "2026-06-21 22:07:41"}],
        "message_archive": [],
    }
    stats = backfill_session_data(info)
    assert stats["normalized"] >= 1
    assert stats["last_activity_updated"] == 1
    from src.utils.admin_timestamp import parse_admin_timestamp

    la = parse_admin_timestamp(info["last_activity"], naive_as_utc=True)
    assert la is not None
    assert la.hour == 7
    assert la.tzinfo is not None


def test_backfill_message_list_sorts_chronologically():
    messages = [
        {"type": "bot", "timestamp": "2026-06-21T12:00:00"},
        {"type": "user", "timestamp": "2026-06-21T10:00:00"},
    ]
    out, _stats = backfill_message_list(messages)
    assert out[0]["type"] == "user"
    assert out[1]["type"] == "bot"
