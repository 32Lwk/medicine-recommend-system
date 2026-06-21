"""admin_timestamp ユーティリティのテスト。"""
from datetime import datetime

from src.utils.admin_timestamp import (
    format_admin_timestamp_iso,
    latest_message_timestamp,
    parse_admin_timestamp,
    sync_last_activity_from_messages,
)
from src.utils.jst_datetime import JST, to_jst_iso


def test_parse_admin_timestamp_legacy_line_utc_naive():
    dt = parse_admin_timestamp("2026-06-21T22:54:34", naive_as_utc=True)
    assert dt is not None
    assert dt.hour == 7
    assert dt.minute == 54
    assert dt.day == 22


def test_parse_admin_timestamp_web_jst_naive():
    dt = parse_admin_timestamp("2026-06-22T16:46:00", naive_as_utc=False)
    assert dt is not None
    assert dt.hour == 16
    assert dt.minute == 46


def test_format_admin_timestamp_iso_web_jst_naive_not_shifted():
    assert (
        format_admin_timestamp_iso("2026-06-22 16:46:00", naive_as_utc=False)
        == "2026-06-22T16:46:00+09:00"
    )


def test_format_admin_timestamp_iso_line_utc_naive():
    assert (
        format_admin_timestamp_iso("2026-06-21 22:54:34", naive_as_utc=True)
        == "2026-06-22T07:54:34+09:00"
    )


def test_format_admin_timestamp_iso_idempotent_for_jst_offset():
    value = "2026-06-22T07:54:34+09:00"
    assert format_admin_timestamp_iso(value, naive_as_utc=True) == value
    assert format_admin_timestamp_iso(value, naive_as_utc=False) == value


def test_latest_message_timestamp_picks_newest_line():
    messages = [
        {"timestamp": "2026-06-21T09:00:00"},
        {"timestamp": "2026-06-21T22:07:41"},
    ]
    latest = latest_message_timestamp(messages, naive_as_utc=True)
    assert latest is not None
    assert latest.day == 22
    assert latest.hour == 7


def test_sync_last_activity_from_messages_line():
    info = {
        "last_activity": datetime(2026, 6, 21, 19, 36, 32),
        "messages": [{"timestamp": "2026-06-21T22:07:41.527824"}],
    }
    sync_last_activity_from_messages(info, naive_as_utc=True)
    synced = parse_admin_timestamp(info["last_activity"], naive_as_utc=True)
    assert synced is not None
    assert to_jst_iso(synced) == "2026-06-22T07:07:41+09:00"


def test_latest_message_timestamp_mixed_naive_and_aware():
    """レガシー naive datetime と JST ISO が混在しても比較エラーにならない。"""
    from src.utils.jst_datetime import now_jst_iso

    messages = [
        {"timestamp": datetime(2026, 6, 21, 19, 36, 32)},
        {"timestamp": "2026-06-21T22:07:41.527824"},
        {"timestamp": now_jst_iso()},
    ]
    latest = latest_message_timestamp(messages, naive_as_utc=True)
    assert latest is not None
    assert latest.tzinfo is not None
