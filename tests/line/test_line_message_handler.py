"""LINE メッセージハンドラの統合テスト（モック）。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.line_message_handler import _deliver_line_messages, _process_text_message


def test_process_text_message_replies_after_pipeline(monkeypatch):
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
        patch("src.handlers.line.line_message_handler.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_loading.run_loading_keepalive", new_callable=AsyncMock),
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock) as mock_reply,
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock) as mock_push,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_message_handler.handle_chat_post_async", new_callable=AsyncMock) as mock_post,
        patch("src.handlers.line.line_message_handler.resolve_latest_bot_message", return_value=bot_msg),
        patch("src.handlers.line.line_message_handler.build_line_messages_from_bot_message", return_value=flex_msgs),
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=True),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.handlers.line.line_feedback.get_session_from_db", return_value={}),
        patch("src.handlers.line.line_feedback.save_session_to_db"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_reply.return_value = True
        mock_post.return_value = ({"status": "ok"}, 200)
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "頭が痛い", "reply-tok"))

    mock_loading.assert_awaited_once()
    mock_reply.assert_awaited_once()
    mock_push.assert_not_awaited()
    mock_post.assert_awaited_once()


def test_process_text_message_progressive_uses_deliver_final(monkeypatch):
    """Physical + carousel 送信済み時は deliver_final_line_messages 経由で Reply。"""
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
                {"product_name": "テスト薬", "explanation": "おすすめです。"},
            ],
        },
    }

    with (
        patch("src.handlers.line.line_message_handler.start_loading_animation", new_callable=AsyncMock),
        patch("src.handlers.line.line_loading.run_loading_keepalive", new_callable=AsyncMock),
        patch("src.handlers.line.line_message_handler.handle_chat_post_async", new_callable=AsyncMock) as mock_post,
        patch("src.handlers.line.line_message_handler.resolve_latest_bot_message", return_value=bot_msg),
        patch(
            "src.handlers.line.line_message_handler.build_line_messages_from_bot_message",
            return_value=[{"type": "flex", "altText": "full"}],
        ),
        patch(
            "src.handlers.line.line_message_handler.deliver_final_line_messages",
            new_callable=AsyncMock,
        ) as mock_deliver_final,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=True),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_post.return_value = ({"status": "ok"}, 200)
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "頭が痛い", "reply-tok"))

    mock_deliver_final.assert_awaited_once()


def test_process_text_message_non_physical_calls_deliver_final(monkeypatch):
    """非 Physical 相談でも deliver_final_line_messages 経由（内部で一括 Flex フォールバック）。"""
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    bot_msg = {
        "type": "bot",
        "diagnosis": {"status": "success", "medicine_type": "解熱鎮痛剤", "recommended_medicines": []},
    }

    with (
        patch("src.handlers.line.line_message_handler.start_loading_animation", new_callable=AsyncMock),
        patch("src.handlers.line.line_loading.run_loading_keepalive", new_callable=AsyncMock),
        patch("src.handlers.line.line_message_handler.handle_chat_post_async", new_callable=AsyncMock) as mock_post,
        patch("src.handlers.line.line_message_handler.resolve_latest_bot_message", return_value=bot_msg),
        patch(
            "src.handlers.line.line_message_handler.build_line_messages_from_bot_message",
            return_value=[{"type": "flex", "altText": "full"}],
        ),
        patch(
            "src.handlers.line.line_message_handler.deliver_final_line_messages",
            new_callable=AsyncMock,
        ) as mock_deliver_final,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=True),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_post.return_value = ({"status": "ok"}, 200)
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "最近眠れない", "reply-tok"))

    mock_deliver_final.assert_awaited_once()


def test_process_text_message_skips_duplicate_without_text(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with (
        patch("src.handlers.line.line_message_handler.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_message_handler.handle_chat_post_async") as mock_post,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=False),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
    ):
        mock_prime.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "こんにちは", "reply-tok"))

    mock_loading.assert_awaited_once()
    mock_post.assert_not_called()


def test_process_text_message_dev_preview_replies_once(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    preview_bot = {
        "type": "bot",
        "diagnosis": {"status": "success", "medicine_type": "解熱鎮痛剤", "recommended_medicines": []},
    }
    flex_msgs = [{"type": "flex", "altText": "a", "contents": {}}]

    with (
        patch("src.handlers.line.line_message_handler.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock) as mock_reply,
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock) as mock_push,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_dev_triggers.try_line_dev_flex_preview", return_value=preview_bot),
        patch("src.handlers.line.line_message_handler.handle_chat_post_async") as mock_post,
        patch(
            "src.handlers.line.line_message_handler.build_line_messages_from_bot_message",
            return_value=flex_msgs,
        ),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.handlers.line.line_feedback.get_session_from_db", return_value={}),
        patch("src.handlers.line.line_feedback.save_session_to_db"),
    ):
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        asyncio.run(_process_text_message("Utest", "mrcdevline00000001", "reply-tok"))

    mock_post.assert_not_called()
    mock_loading.assert_not_awaited()
    mock_reply.assert_awaited_once()
    mock_push.assert_not_awaited()
    pushed = mock_reply.await_args.args[1]
    assert pushed[0].get("quickReply")


def test_deliver_falls_back_to_push_when_reply_fails(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    flex = [{"type": "flex", "altText": "おすすめ", "contents": {}}]

    with (
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock, return_value=False),
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock, return_value=True) as mock_push,
    ):
        asyncio.run(_deliver_line_messages("Utest", flex, reply_token="tok"))

    mock_push.assert_awaited_once()
    assert len(mock_push.await_args.args[1]) == 1


def test_deliver_push_chunk_falls_back_to_alt_text(monkeypatch):
    from src.handlers.line.line_message_handler import _push_message_chunk

    calls: list[list] = []

    async def fake_push(user_id, messages):
        calls.append(messages)
        return messages[0].get("type") == "text"

    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.push_messages",
        fake_push,
    )
    flex = {"type": "flex", "altText": "おすすめのお薬", "contents": {}}
    asyncio.run(_push_message_chunk("Utest", [flex]))
    assert len(calls) == 3
    assert calls[0][0]["type"] == "flex"
    assert calls[1][0]["type"] == "flex"
    assert calls[2][0]["type"] == "text"
    assert calls[2][0]["text"] == "おすすめのお薬"
