"""JST datetime ヘルパーのテスト。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.utils.jst_datetime import JST, epoch_ms_to_jst_iso, now_jst_iso, to_jst_iso


def test_epoch_ms_to_jst_iso():
    dt = datetime(2026, 6, 22, 7, 47, 44, tzinfo=JST)
    ms = int(dt.timestamp() * 1000)
    iso = epoch_ms_to_jst_iso(ms)
    assert iso == "2026-06-22T07:47:44+09:00"


def test_to_jst_iso_from_utc_naive():
    naive = datetime(2026, 6, 21, 22, 54, 34)
    assert to_jst_iso(naive) == "2026-06-22T07:54:34+09:00"


def test_now_jst_iso_has_offset():
    iso = now_jst_iso()
    assert "+09:00" in iso
