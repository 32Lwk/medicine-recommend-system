"""LINE 非テキストメッセージの案内・スタンプ解釈。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_message_handler import _dispatch_event
from src.handlers.line.line_non_text import (
    STICKER_UNSUPPORTED_REPLY,
    build_non_text_reply,
    try_resolve_sticker_as_text,
)


def test_build_non_text_reply_image():
    text = build_non_text_reply("image")
    assert "画像" in text
    assert "まだ対応していません" in text
    assert "テキスト" in text


def test_build_non_text_reply_audio():
    text = build_non_text_reply("audio")
    assert "音声" in text
    assert "まだ対応していません" in text


def test_build_non_text_reply_unknown_type():
    text = build_non_text_reply("foo")
    assert "まだ対応していません" in text


def test_sticker_keywords_greeting():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "1",
            "stickerId": "1",
            "keywords": ["こんにちは"],
        }
    ) == "こんにちは"


def test_sticker_keywords_thanks():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "1",
            "stickerId": "1",
            "keywords": ["ありがとう"],
        }
    ) == "ありがとう"


def test_sticker_keywords_english_greeting():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "1",
            "stickerId": "1",
            "keywords": ["Hello"],
        }
    ) == "Hello"


def test_sticker_known_package_mapping():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "11537",
            "stickerId": "52002738",
        }
    ) == "こんにちは"


def test_sticker_yurukeigo_pack_thanks():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "8515",
            "stickerId": "16581243",
        }
    ) == "ありがとうございます"


def test_sticker_variant_pack_propagated():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "8522",
            "stickerId": "16581284",
        }
    ) == "おはようございます"


def test_sticker_yoroshiku_greeting():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "8515",
            "stickerId": "16581248",
        }
    ) == "よろしくお願いします"


def test_sticker_unknown_returns_none():
    assert try_resolve_sticker_as_text(
        {
            "type": "sticker",
            "packageId": "99999",
            "stickerId": "99999",
        }
    ) is None


def test_dispatch_image_sends_type_specific_reply(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with patch(
        "src.handlers.line.line_message_handler._dispatch_quick_text_reply",
        new_callable=AsyncMock,
    ) as mock_reply:
        asyncio.run(
            _dispatch_event(
                {
                    "type": "message",
                    "replyToken": "tok",
                    "source": {"type": "user", "userId": "U1"},
                    "message": {"type": "image", "id": "mid"},
                }
            )
        )
    mock_reply.assert_awaited_once()
    sent_text = mock_reply.await_args.args[2]
    assert "画像" in sent_text
    assert sent_text != STICKER_UNSUPPORTED_REPLY


def test_dispatch_greeting_sticker_routes_to_pipeline(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with (
        patch(
            "src.handlers.line.line_message_handler._process_text_message",
            new_callable=AsyncMock,
        ) as mock_proc,
        patch(
            "src.handlers.line.line_message_handler._dispatch_quick_text_reply",
            new_callable=AsyncMock,
        ) as mock_quick,
    ):
        asyncio.run(
            _dispatch_event(
                {
                    "type": "message",
                    "replyToken": "tok",
                    "source": {"type": "user", "userId": "U1"},
                    "message": {
                        "type": "sticker",
                        "packageId": "11537",
                        "stickerId": "52002738",
                    },
                }
            )
        )
    mock_proc.assert_awaited_once()
    assert mock_proc.await_args.args[:3] == ("U1", "こんにちは", "tok")
    mock_quick.assert_not_awaited()


def test_dispatch_unknown_sticker_sends_sticker_reply(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with (
        patch(
            "src.handlers.line.line_message_handler._process_text_message",
            new_callable=AsyncMock,
        ) as mock_proc,
        patch(
            "src.handlers.line.line_message_handler._dispatch_quick_text_reply",
            new_callable=AsyncMock,
        ) as mock_quick,
    ):
        asyncio.run(
            _dispatch_event(
                {
                    "type": "message",
                    "replyToken": "tok",
                    "source": {"type": "user", "userId": "U1"},
                    "message": {
                        "type": "sticker",
                        "packageId": "99999",
                        "stickerId": "99999",
                    },
                }
            )
        )
    mock_proc.assert_not_awaited()
    mock_quick.assert_awaited_once()
    assert mock_quick.await_args.args[2] == STICKER_UNSUPPORTED_REPLY
