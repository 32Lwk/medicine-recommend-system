"""LINE 配信（Reply 優先・二重送信防止）のテスト。"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_delivery import (
    REPLY_TOKEN_BUDGET_MS,
    deliver_line_messages,
    reply_token_likely_valid,
    should_try_reply,
)
from src.handlers.line.line_progressive_delivery import (
    LineDeliveryContext,
    set_line_delivery_context,
)


def test_reply_token_likely_valid_within_budget():
    now_ms = int(time.time() * 1000)
    assert reply_token_likely_valid(now_ms - 5_000) is True
    assert reply_token_likely_valid(now_ms - REPLY_TOKEN_BUDGET_MS - 1) is False


def test_should_try_reply_skips_expired_token():
    now_ms = int(time.time() * 1000)
    with patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"):
        assert should_try_reply("tok", event_timestamp_ms=now_ms - 5_000) is True
        assert should_try_reply("tok", event_timestamp_ms=now_ms - REPLY_TOKEN_BUDGET_MS - 1) is False


def test_deliver_line_messages_uses_reply_first():
    reply_fn = AsyncMock(return_value=True)
    push_fn = AsyncMock(return_value=True)
    with patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"):
        asyncio.run(
            deliver_line_messages(
                "U1",
                [{"type": "text", "text": "hello"}],
                reply_token="tok",
                reply_fn=reply_fn,
                push_chunk_fn=push_fn,
                event_timestamp_ms=int(time.time() * 1000),
            )
        )
    reply_fn.assert_awaited_once()
    push_fn.assert_not_awaited()


def test_deliver_line_messages_skips_duplicate_in_same_context():
    ctx = LineDeliveryContext(
        user_id="U1",
        reply_token="tok",
        lang="ja",
        sid="line:U1",
        delivered=True,
    )
    set_line_delivery_context(ctx)
    reply_fn = AsyncMock(return_value=True)
    push_fn = AsyncMock(return_value=True)
    with patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"):
        try:
            ok = asyncio.run(
                deliver_line_messages(
                    "U1",
                    [{"type": "text", "text": "hello"}],
                    reply_token="tok",
                    reply_fn=reply_fn,
                    push_chunk_fn=push_fn,
                )
            )
        finally:
            set_line_delivery_context(None)
    assert ok is False
    reply_fn.assert_not_awaited()
    push_fn.assert_not_awaited()


def test_deliver_line_messages_push_fallback_when_reply_fails():
    reply_fn = AsyncMock(return_value=False)
    push_fn = AsyncMock(return_value=True)
    with patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"):
        ok = asyncio.run(
            deliver_line_messages(
                "U1",
                [{"type": "text", "text": "hello"}],
                reply_token="tok",
                reply_fn=reply_fn,
                push_chunk_fn=push_fn,
                event_timestamp_ms=int(time.time() * 1000),
            )
        )
    assert ok is True
    reply_fn.assert_awaited_once()
    push_fn.assert_awaited_once()
