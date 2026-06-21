"""LINE セッションの DB 上メッセージ日時を正規化・補正する。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from src.services.session_lifecycle import sort_messages_chronologically
from src.utils.admin_timestamp import (
    format_admin_timestamp_iso,
    latest_message_timestamp,
    parse_admin_timestamp,
    sync_last_activity_from_messages,
)

logger = logging.getLogger(__name__)

_PAIR_MIN_GAP = timedelta(milliseconds=1)


def _is_line_session_id(session_id: str | None) -> bool:
    try:
        from src.handlers.line.line_session import is_line_session_id

        return is_line_session_id(session_id)
    except ImportError:
        return bool(session_id and str(session_id).lower().startswith("line:"))


def normalize_message_timestamp_value(value: Any) -> tuple[str | None, bool]:
    """timestamp を ISO 文字列へ。変更があれば changed=True。"""
    if value is None or value == "":
        return None, False
    normalized = format_admin_timestamp_iso(value)
    if not normalized:
        return None, False
    original = str(value).strip()
    if original == normalized:
        return normalized, False
    return normalized, True


def fix_reply_order_timestamps(messages: list[dict]) -> int:
    """
    同一やり取りで bot の timestamp が user 以前になっている場合、
    直前 user の 1ms 後へ補正する。
    """
    if not messages:
        return 0
    fixed = 0
    prev_user_ts: datetime | None = None
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("type") == "user":
            prev_user_ts = parse_admin_timestamp(msg.get("timestamp"))
            continue
        if msg.get("type") != "bot" or prev_user_ts is None:
            continue
        bot_ts = parse_admin_timestamp(msg.get("timestamp"))
        if bot_ts is None or bot_ts <= prev_user_ts:
            new_ts = (prev_user_ts + _PAIR_MIN_GAP).isoformat()
            msg["timestamp"] = new_ts
            fixed += 1
    return fixed


def backfill_message_list(messages: list | None) -> tuple[list[dict], dict[str, int]]:
    """メッセージ配列の timestamp を正規化し、欠損を補間して時系列整列。"""
    stats = {
        "messages": 0,
        "normalized": 0,
        "filled_missing": 0,
        "reply_order_fixed": 0,
        "reordered": 0,
    }
    items = [dict(m) for m in (messages or []) if isinstance(m, dict)]
    if not items:
        return [], stats

    stats["messages"] = len(items)
    before_keys = [
        (m.get("uuid"), m.get("type"), m.get("timestamp"), (m.get("content") or "")[:80])
        for m in items
    ]

    for msg in items:
        ts, changed = normalize_message_timestamp_value(msg.get("timestamp"))
        if ts:
            if changed:
                stats["normalized"] += 1
            msg["timestamp"] = ts
        else:
            msg.pop("timestamp", None)

    sorted_msgs = sort_messages_chronologically(items)
    after_keys = [
        (m.get("uuid"), m.get("type"), m.get("timestamp"), (m.get("content") or "")[:80])
        for m in sorted_msgs
    ]
    if before_keys != after_keys:
        stats["reordered"] = 1

    for msg in sorted_msgs:
        if not msg.get("timestamp"):
            stats["filled_missing"] += 1

    stats["reply_order_fixed"] = fix_reply_order_timestamps(sorted_msgs)
    return sorted_msgs, stats


def backfill_session_data(session_data: dict) -> dict[str, int]:
    """単一セッション dict をインプレース更新。統計を返す。"""
    totals = {
        "sessions": 1,
        "messages": 0,
        "normalized": 0,
        "filled_missing": 0,
        "reply_order_fixed": 0,
        "reordered": 0,
        "last_activity_updated": 0,
    }
    if not isinstance(session_data, dict):
        return totals

    for key in ("messages", "message_archive"):
        updated, stats = backfill_message_list(session_data.get(key))
        session_data[key] = updated
        for k in ("messages", "normalized", "filled_missing", "reply_order_fixed", "reordered"):
            totals[k] += stats.get(k, 0)

    before_la = parse_admin_timestamp(session_data.get("last_activity"))
    sync_last_activity_from_messages(session_data)
    latest = latest_message_timestamp(
        (session_data.get("message_archive") or []) + (session_data.get("messages") or [])
    )
    if latest is not None:
        session_data["last_activity"] = latest
    after_la = parse_admin_timestamp(session_data.get("last_activity"))
    if before_la != after_la:
        totals["last_activity_updated"] = 1
    return totals


def backfill_line_sessions_in_db(*, dry_run: bool = False) -> dict[str, Any]:
    """
    DB 内の LINE セッションを走査し timestamp / last_activity を補正する。

    LINE Messaging API には過去のチャット履歴取得 API がないため、
    保存済み timestamp の正規化・欠損補間・last_activity 同期のみ行う。
    """
    from src.services.database import get_database, init_database
    from src.services.session_manager import save_session_to_db

    init_database()
    db = get_database()
    if not db or not db.is_available():
        return {"ok": False, "error": "database_unavailable"}

    sessions = db.get_all_sessions()
    summary: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "line_api_note": (
            "LINE Messaging API には1対1チャットの過去メッセージ一覧取得 API がないため、"
            "DB に保存済みの timestamp を正規化・補正します。"
        ),
        "sessions_scanned": 0,
        "sessions_updated": 0,
        "messages": 0,
        "normalized": 0,
        "filled_missing": 0,
        "reply_order_fixed": 0,
        "reordered": 0,
        "last_activity_updated": 0,
        "session_ids": [],
    }

    for row in sessions:
        sid = str(row.get("session_id") or "")
        if not _is_line_session_id(sid):
            continue
        summary["sessions_scanned"] += 1
        stats = backfill_session_data(row)
        changed = (
            stats["normalized"] > 0
            or stats["filled_missing"] > 0
            or stats["reply_order_fixed"] > 0
            or stats["reordered"] > 0
            or stats["last_activity_updated"] > 0
        )
        for key in (
            "messages",
            "normalized",
            "filled_missing",
            "reply_order_fixed",
            "reordered",
            "last_activity_updated",
        ):
            summary[key] += stats.get(key, 0)
        if changed:
            summary["sessions_updated"] += 1
            summary["session_ids"].append(sid)
            if not dry_run:
                save_session_to_db(sid, row)
                logger.info("Backfilled LINE session timestamps sid=%s", sid)

    return summary
