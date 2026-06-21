"""LINE Webhook イベント時刻をセッションメッセージ timestamp に反映する。"""
from __future__ import annotations

from typing import Any

from src.utils.jst_datetime import epoch_ms_to_jst_iso, now_jst_iso


def line_event_ms_to_iso(ms: int | float) -> str:
    """LINE イベント timestamp（ミリ秒）を JST ISO 文字列へ変換する。"""
    return epoch_ms_to_jst_iso(ms)


def line_event_timestamp_ms(event: dict[str, Any] | None) -> int | None:
    if not event:
        return None
    raw = event.get("timestamp")
    if isinstance(raw, (int, float)):
        return int(raw)
    return None


def resolve_inbound_message_timestamp() -> str:
    """
    受信メッセージの timestamp。

    LINE Webhook 処理中はイベント時刻（ユーザーが LINE 上で送った時刻）を優先し、
    それ以外はサーバー現地時刻。
    """
    try:
        from src.handlers.line.line_progressive_delivery import get_line_delivery_context

        ctx = get_line_delivery_context()
        if ctx and ctx.event_timestamp_ms is not None:
            return line_event_ms_to_iso(ctx.event_timestamp_ms)
    except ImportError:
        pass
    return now_jst_iso()
