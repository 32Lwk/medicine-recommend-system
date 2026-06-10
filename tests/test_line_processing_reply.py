"""LINE 処理中 UX（loading animation / 二重送信文言）のテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_processing_reply import line_processing_busy_text
from src.handlers.line.line_reply import _normalize_loading_seconds, start_loading_animation


def test_normalize_loading_seconds():
    assert _normalize_loading_seconds(3) == 5
    assert _normalize_loading_seconds(62) == 60
    assert _normalize_loading_seconds(58) == 60


def test_processing_busy_text_i18n():
    assert "完了後" in line_processing_busy_text("ja")
    assert "in progress" in line_processing_busy_text("en")


def test_start_loading_animation_posts_chat_id():
    with patch("src.handlers.line.line_reply._post_json", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = True
        ok = asyncio.run(start_loading_animation("Utest123", loading_seconds=60))
    assert ok is True
    mock_post.assert_awaited_once()
    assert mock_post.await_args.args[0].endswith("/chat/loading/start")
    payload = mock_post.await_args.args[1]
    assert payload["chatId"] == "Utest123"
    assert payload["loadingSeconds"] == 60
