"""admin_timestamp ユーティリティのテスト。"""
from datetime import datetime

from src.utils.admin_timestamp import (
    format_admin_timestamp_iso,
    latest_message_timestamp,
    parse_admin_timestamp,
    sync_last_activity_from_messages,
)


def test_parse_admin_timestamp_iso_string():
    dt = parse_admin_timestamp("2026-06-21T22:07:41.527824")
    assert dt is not None
    assert dt.hour == 22
    assert dt.minute == 7


def test_parse_admin_timestamp_space_separated():
    dt = parse_admin_timestamp("2026-06-21 22:07:41")
    assert dt is not None
    assert dt.hour == 22


def test_parse_admin_timestamp_unix_seconds():
    dt = parse_admin_timestamp(1718982461)
    assert dt is not None
    assert dt.year == 2024


def test_parse_admin_timestamp_unix_milliseconds():
    dt = parse_admin_timestamp(1718982461000)
    assert dt is not None
    assert dt.year == 2024


def test_latest_message_timestamp_picks_newest():
    messages = [
        {"timestamp": "2026-06-21T09:00:00"},
        {"timestamp": "2026-06-21T22:07:41"},
    ]
    latest = latest_message_timestamp(messages)
    assert latest is not None
    assert latest.hour == 22


def test_sync_last_activity_from_messages():
    info = {
        "last_activity": datetime(2026, 6, 21, 19, 36, 32),
        "messages": [{"timestamp": "2026-06-21T22:07:41.527824"}],
    }
    sync_last_activity_from_messages(info)
    synced = parse_admin_timestamp(info["last_activity"])
    assert synced is not None
    assert synced.hour == 22
    assert synced.minute == 7


def test_format_admin_timestamp_iso():
    assert format_admin_timestamp_iso("2026-06-21 22:07:41") == "2026-06-21T22:07:41"
