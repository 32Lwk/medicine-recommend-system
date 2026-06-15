"""LINE 応答配信（Reply 優先・二重送信防止）。"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from config.line_config import get_line_channel_access_token
from src.handlers.line.line_progressive_delivery import get_line_delivery_context

logger = logging.getLogger(__name__)

# LINE reply token は秒単位で失効する。イベント timestamp からの経過で判定する。
REPLY_TOKEN_BUDGET_MS = 22_000

PushChunkFn = Callable[[str, list[dict[str, Any]]], Awaitable[bool]]
ReplyFn = Callable[[str, list[dict[str, Any]]], Awaitable[bool]]


def reply_token_likely_valid(event_timestamp_ms: int | None) -> bool:
    """ユーザー送信時刻から reply token がまだ有効と見なせるか。"""
    if not event_timestamp_ms:
        return True
    elapsed_ms = (time.time() * 1000) - float(event_timestamp_ms)
    return elapsed_ms < REPLY_TOKEN_BUDGET_MS


def should_try_reply(
    reply_token: str | None,
    *,
    event_timestamp_ms: int | None = None,
) -> bool:
    if not reply_token or not get_line_channel_access_token():
        return False
    if not reply_token_likely_valid(event_timestamp_ms):
        logger.info(
            "LINE reply token likely expired elapsed_ms=%.0f; will use push",
            (time.time() * 1000) - float(event_timestamp_ms or 0),
        )
        return False
    return True


async def deliver_line_messages(
    user_id: str,
    messages: list[dict[str, Any]],
    *,
    reply_token: str | None = None,
    reply_fn: ReplyFn,
    push_chunk_fn: PushChunkFn,
    event_timestamp_ms: int | None = None,
    force: bool = False,
) -> bool:
    """
    Reply API を優先し、失効時のみ Push へフォールバックする。
    同一処理内の二重配信は LineDeliveryContext.delivered で抑止する。

    Returns:
        True if at least one message was delivered.
    """
    if not messages:
        return False

    ctx = get_line_delivery_context()
    if not force and ctx is not None and ctx.delivered:
        logger.info("LINE delivery skipped in-process duplicate userId=%s", user_id)
        return False

    effective_ts = event_timestamp_ms
    if effective_ts is None and ctx is not None:
        effective_ts = ctx.event_timestamp_ms

    chunks = [messages[i : i + 5] for i in range(0, len(messages), 5)]
    token = reply_token or (ctx.reply_token if ctx else None)

    if should_try_reply(token, event_timestamp_ms=effective_ts):
        if await reply_fn(token, chunks[0]):
            logger.info("LINE reply ok userId=%s messages=%s", user_id, len(chunks[0]))
            for chunk in chunks[1:]:
                await push_chunk_fn(user_id, chunk)
            if ctx is not None:
                ctx.delivered = True
            return True
        logger.warning("LINE reply failed; falling back to push userId=%s", user_id)

    delivered = False
    for chunk in chunks:
        if await push_chunk_fn(user_id, chunk):
            delivered = True
    if delivered and ctx is not None:
        ctx.delivered = True
    return delivered
