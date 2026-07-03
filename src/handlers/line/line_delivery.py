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

_SLOW_CONCIERGE_INTENTS = frozenset(
    {
        "greeting",
        "thanks",
        "chitchat",
        "redirect",
        "doc_operator",
        "doc_privacy",
        "doc_terms",
        "doc_consultation",
        "doc_app_overview",
        "doc_changelog",
        "capabilities",
        "architecture",
        "app_about",
    }
)

PushChunkFn = Callable[[str, list[dict[str, Any]]], Awaitable[bool]]
ReplyFn = Callable[[str, list[dict[str, Any]]], Awaitable[bool]]


def reply_token_elapsed_ms(event_timestamp_ms: int | None) -> float | None:
    if not event_timestamp_ms:
        return None
    return (time.time() * 1000) - float(event_timestamp_ms)


def reply_token_likely_valid(event_timestamp_ms: int | None) -> bool:
    """ユーザー送信時刻から reply token がまだ有効と見なせるか。"""
    elapsed = reply_token_elapsed_ms(event_timestamp_ms)
    if elapsed is None:
        return True
    return elapsed < REPLY_TOKEN_BUDGET_MS


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
            reply_token_elapsed_ms(event_timestamp_ms) or 0,
        )
        return False
    return True


def is_slow_concierge_delivery(bot_message: dict[str, Any] | None) -> bool:
    """監査ログ用: Concierge 等の遅い経路か（配信方針は Reply 優先のまま）。"""
    if not bot_message:
        return False
    if bot_message.get("greeting"):
        return True
    return bot_message.get("concierge_intent") in _SLOW_CONCIERGE_INTENTS


def _record_delivery_perf(
    *,
    delivery_mode: str,
    event_timestamp_ms: int | None,
    slow_path: bool,
) -> None:
    try:
        from src.services.pipeline_perf import mark_pipeline_step, record_pipeline_perf

        mark_pipeline_step("delivery_mode")
        record_pipeline_perf(
            delivery_mode=delivery_mode,
            reply_token_elapsed_ms=reply_token_elapsed_ms(event_timestamp_ms),
            slow_concierge_path=slow_path,
        )
    except Exception:
        pass


async def deliver_line_messages(
    user_id: str,
    messages: list[dict[str, Any]],
    *,
    reply_token: str | None = None,
    reply_fn: ReplyFn,
    push_chunk_fn: PushChunkFn,
    event_timestamp_ms: int | None = None,
    force: bool = False,
    bot_message: dict[str, Any] | None = None,
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

    slow_path = is_slow_concierge_delivery(bot_message)

    chunks = [messages[i : i + 5] for i in range(0, len(messages), 5)]
    token = reply_token or (ctx.reply_token if ctx else None)

    if should_try_reply(token, event_timestamp_ms=effective_ts):
        if await reply_fn(token, chunks[0]):
            logger.info("LINE reply ok userId=%s messages=%s", user_id, len(chunks[0]))
            for chunk in chunks[1:]:
                await push_chunk_fn(user_id, chunk)
            if ctx is not None:
                ctx.delivered = True
            _record_delivery_perf(
                delivery_mode="reply",
                event_timestamp_ms=effective_ts,
                slow_path=slow_path,
            )
            return True
        if ctx is not None and ctx.reply_token_unavailable:
            logger.info(
                "LINE reply token unavailable; skip push fallback (likely duplicate webhook) userId=%s",
                user_id,
            )
            ctx.delivered = True
            _record_delivery_perf(
                delivery_mode="reply_token_unavailable",
                event_timestamp_ms=effective_ts,
                slow_path=slow_path,
            )
            return False
        logger.warning("LINE reply failed; falling back to push userId=%s", user_id)

    delivered = False
    for chunk in chunks:
        if await push_chunk_fn(user_id, chunk):
            delivered = True
    if delivered and ctx is not None:
        ctx.delivered = True
    mode = "push" if not token else "reply_fallback_push"
    _record_delivery_perf(
        delivery_mode=mode,
        event_timestamp_ms=effective_ts,
        slow_path=slow_path,
    )
    return delivered
