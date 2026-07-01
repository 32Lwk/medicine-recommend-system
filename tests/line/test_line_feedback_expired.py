"""LINE フィードバック期限切れ postback。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_feedback import handle_line_feedback_postback


def test_expired_feedback_replies_with_message():
    async def _run():
        with patch(
            "src.handlers.line.line_feedback._load_pending_context",
            return_value=None,
        ), patch(
            "src.handlers.line.line_reply.reply_messages",
            new_callable=AsyncMock,
        ) as mock_reply, patch(
            "config.line_config.LINE_CHANNEL_ACCESS_TOKEN",
            "token",
        ):
            await handle_line_feedback_postback(
                "Utest",
                "mrcfb|pos|abcd1234",
                reply_token="rtok",
            )
            mock_reply.assert_awaited_once()
            text = mock_reply.await_args[0][1][0]["text"]
            assert "期限" in text

    asyncio.run(_run())
