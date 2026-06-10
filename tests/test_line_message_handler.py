"""LINE メッセージハンドラの統合テスト（モック）。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.line_message_handler import _process_text_message


def test_process_text_message_pushes_flex(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    bot_msg = {
        "type": "bot",
        "diagnosis": {
            "status": "success",
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [
                {
                    "product_name": "テスト薬",
                    "manufacturer": "A社",
                    "efficacy": "頭痛",
                    "explanation": "おすすめです。",
                    "display_score": 80,
                }
            ],
        },
    }
    flex_msgs = [
        {"type": "flex", "altText": "a", "contents": {}},
        {"type": "flex", "altText": "b", "contents": {}},
    ]

    with (
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock) as mock_reply,
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock) as mock_push,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_message_handler.handle_chat_post", return_value=({"status": "ok"}, 200)),
        patch("src.handlers.line.line_message_handler.get_latest_bot_message", return_value=bot_msg),
        patch("src.handlers.line.line_message_handler.build_line_messages_from_bot_message", return_value=flex_msgs),
        patch("src.services.chat_inflight.is_chat_job_in_flight", return_value=False),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "頭が痛い", "reply-tok"))

    mock_reply.assert_awaited_once()
    assert mock_push.await_count == 2
