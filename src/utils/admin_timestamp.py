"""管理画面向けタイムスタンプの正規化。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.utils.jst_datetime import JST, to_jst_iso


def _coerce_numeric_timestamp(raw: int | float) -> float:
    """Unix 秒またはミリ秒を秒に正規化する。"""
    value = float(raw)
    if value >= 1e12:
        return value / 1000.0
    return value


def parse_admin_timestamp(value: Any) -> datetime | None:
    """混在フォーマットのタイムスタンプを datetime に変換する。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(_coerce_numeric_timestamp(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit() or (
        text.replace(".", "", 1).isdigit() and text.count(".") <= 1
    ):
        try:
            return datetime.fromtimestamp(_coerce_numeric_timestamp(float(text)), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def format_admin_timestamp_iso(value: Any) -> str | None:
    """JSON API 向け JST ISO 文字列。"""
    parsed = parse_admin_timestamp(value)
    if parsed is None:
        return None
    return to_jst_iso(parsed)


def latest_message_timestamp(messages: list | None) -> datetime | None:
    """メッセージ一覧から最も新しい timestamp を返す。"""
    latest: datetime | None = None
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        parsed = parse_admin_timestamp(msg.get("timestamp"))
        if parsed is None:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def sync_last_activity_from_messages(session_data: dict) -> None:
    """last_activity を messages / message_archive の最新時刻に合わせる。"""
    if not isinstance(session_data, dict):
        return
    candidates: list[datetime] = []
    for key in ("messages", "message_archive"):
        latest = latest_message_timestamp(session_data.get(key))
        if latest is not None:
            candidates.append(_as_utc_aware(latest))
    existing = parse_admin_timestamp(session_data.get("last_activity"))
    if existing is not None:
        candidates.append(_as_utc_aware(existing))
    if not candidates:
        return
    session_data["last_activity"] = to_jst_iso(max(candidates))


def normalize_message_timestamps(messages: list | None) -> list:
    """管理画面 API 応答用に各メッセージ timestamp を ISO 文字列へ統一。"""
    out: list = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        normalized = dict(msg)
        ts = format_admin_timestamp_iso(msg.get("timestamp"))
        if ts:
            normalized["timestamp"] = ts
        out.append(normalized)
    return out
