"""LINE Reply / Push API クライアントのテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.handlers.line import line_reply


def test_reply_messages_sends_authorization(monkeypatch):
    monkeypatch.setattr(line_reply, "get_line_channel_access_token", lambda: "test-token")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""
    client = AsyncMock()
    client.is_closed = False
    client.post = AsyncMock(return_value=mock_response)
    line_reply.set_http_client(client)

    ok = asyncio.run(
        line_reply.reply_messages(
            "reply-token-1",
            [{"type": "text", "text": "hello"}],
        )
    )
    assert ok is True
    client.post.assert_awaited_once()
    args, kwargs = client.post.call_args
    assert args[0] == line_reply.LINE_REPLY_URL
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["json"]["replyToken"] == "reply-token-1"


def test_push_skipped_without_token(monkeypatch):
    monkeypatch.setattr(line_reply, "get_line_channel_access_token", lambda: "")
    line_reply.set_http_client(AsyncMock())
    ok = asyncio.run(line_reply.push_messages("U123", [{"type": "text", "text": "x"}]))
    assert ok is False
