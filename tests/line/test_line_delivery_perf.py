"""LINE 配信 PIPELINE_PERF ログ（Reply 優先・計測のみ）"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_delivery import (
    REPLY_TOKEN_BUDGET_MS,
    deliver_line_messages,
    is_slow_concierge_delivery,
)
from src.services.pipeline_perf import bind_pipeline_perf, log_pipeline_perf


def test_slow_concierge_detection_for_logging():
    assert is_slow_concierge_delivery({"greeting": True}) is True
    assert is_slow_concierge_delivery({"concierge_intent": "greeting"}) is True
    assert is_slow_concierge_delivery({"concierge_intent": "Physical"}) is False


def test_greeting_delivery_logs_reply_mode_with_expired_token():
    sid = "line-greeting-perf"
    bind_pipeline_perf(sid=sid, channel="line")
    reply_fn = AsyncMock(return_value=True)
    push_fn = AsyncMock(return_value=True)
    expired_ts = int(time.time() * 1000) - REPLY_TOKEN_BUDGET_MS - 5_000
    bot_message = {"greeting": True, "concierge_intent": "greeting"}

    with patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"):
        asyncio.run(
            deliver_line_messages(
                "U1",
                [{"type": "text", "text": "こんにちは"}],
                reply_token="tok",
                reply_fn=reply_fn,
                push_chunk_fn=push_fn,
                event_timestamp_ms=expired_ts,
                bot_message=bot_message,
            )
        )

    with patch("src.services.pipeline_perf.logger") as mock_logger:
        log_pipeline_perf(sid=sid)
        payload = mock_logger.info.call_args[0][1]

    assert payload["delivery_mode"] == "reply_fallback_push"
    assert payload["slow_concierge_path"] is True
    assert payload["reply_token_elapsed_ms"] > REPLY_TOKEN_BUDGET_MS
    push_fn.assert_awaited()
    reply_fn.assert_not_awaited()


def test_valid_token_still_uses_reply():
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
