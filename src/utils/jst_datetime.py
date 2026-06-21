"""日本標準時 (JST) 向け datetime ヘルパー。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_iso(*, timespec: str = "seconds") -> str:
    return now_jst().isoformat(timespec=timespec)


def epoch_ms_to_jst_iso(ms: int | float, *, timespec: str = "seconds") -> str:
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=JST).isoformat(timespec=timespec)


def epoch_sec_to_jst_iso(sec: int | float, *, timespec: str = "seconds") -> str:
    return datetime.fromtimestamp(float(sec), tz=JST).isoformat(timespec=timespec)


def to_jst_iso(value: datetime, *, timespec: str = "seconds") -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(JST).isoformat(timespec=timespec)
