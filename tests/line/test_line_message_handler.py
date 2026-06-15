"""LINE メッセージハンドラの統合テスト（モック）。"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.line_message_handler import (
    _deliver_line_messages,
    _dispatch_event,
    _process_text_message,
)


def test_process_text_message_job_lock_before_loading(monkeypatch):
    """job lock 取得成功後にのみ loading/start を dispatch する。"""
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    call_order: list[str] = []

    def _track_lock(*_args, **_kwargs):
        call_order.append("lock")
        return True

    async def _track_loading(*_args, **_kwargs):
        call_order.append("loading")
        return True

    with (
        patch(
            "src.handlers.line.line_loading.start_loading_animation",
            side_effect=_track_loading,
        ),
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", side_effect=_track_lock),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
        patch("src.handlers.line.line_message_handler.handle_chat_post_async", new_callable=AsyncMock),
        patch("src.handlers.line.line_message_handler.resolve_latest_bot_message", return_value=None),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "頭が痛い", "reply-tok"))

    assert call_order == ["lock", "loading"]


def test_process_text_message_replies_after_pipeline(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
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
        patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock) as mock_reply,
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock) as mock_push,
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_message_handler.handle_chat_post_async", new_callable=AsyncMock) as mock_post,
        patch("src.handlers.line.line_message_handler.resolve_latest_bot_message", return_value=bot_msg),
        patch("src.handlers.line.line_message_handler.build_line_messages_from_bot_message", return_value=flex_msgs),
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=True),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.handlers.line.line_feedback._persist_pending_map"),
        patch("src.services.processing_status.set_processing_language"),
        patch("src.services.processing_status.mark_processing_step"),
        patch("src.services.processing_status.clear_processing_status") as mock_clear_status,
        patch("src.handlers.line.line_message_handler.get_global_monitor") as mock_monitor,
    ):
        mock_reply.return_value = True
        mock_post.return_value = ({"status": "ok"}, 200)
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        mock_monitor.return_value = MagicMock()
        asyncio.run(
            _process_text_message(
                "Utest",
                "頭が痛い",
                "reply-tok",
                event={"timestamp": int(time.time() * 1000), "webhookEventId": "evt-reply-1"},
            )
        )

    mock_loading.assert_awaited_once()
    mock_reply.assert_awaited_once()
    mock_push.assert_not_awaited()
    mock_post.assert_awaited_once()
    mock_clear_status.assert_called_once_with("line:Utest")


def test_process_text_message_progressive_uses_deliver_final(monkeypatch):
    """Physical + carousel 送信済み時は deliver_final_line_messages 経由で Reply。"""
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
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
        patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock),
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
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    bot_msg = {
        "type": "bot",
        "diagnosis": {"status": "success", "medicine_type": "解熱鎮痛剤", "recommended_medicines": []},
    }

    with (
        patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock),
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


def test_process_text_message_skips_duplicate_without_loading(monkeypatch):
    """重複 Webhook は job lock で弾き、loading/start もパイプラインも走らない。"""
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with (
        patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_message_handler.handle_chat_post_async") as mock_post,
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_job_lock.LineJobLock.acquire", return_value=False),
        patch("src.handlers.line.line_job_lock.LineJobLock.release"),
    ):
        mock_prime.return_value = MagicMock()
        asyncio.run(_process_text_message("Utest", "こんにちは", "reply-tok"))

    mock_loading.assert_not_awaited()
    mock_post.assert_not_called()


def test_process_text_message_dev_preview_replies_once(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    monkeypatch.setattr(
        "src.handlers.line.line_loading.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    preview_bot = {
        "type": "bot",
        "diagnosis": {"status": "success", "medicine_type": "解熱鎮痛剤", "recommended_medicines": []},
    }
    flex_msgs = [{"type": "flex", "altText": "a", "contents": {}}]

    with (
        patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock) as mock_loading,
        patch("src.handlers.line.line_message_handler.reply_messages", new_callable=AsyncMock) as mock_reply,
        patch("src.handlers.line.line_message_handler.push_messages", new_callable=AsyncMock) as mock_push,
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
        patch("src.handlers.line.line_message_handler.prime_line_session") as mock_prime,
        patch("src.handlers.line.line_dev_triggers.try_line_dev_flex_preview", return_value=preview_bot),
        patch("src.handlers.line.line_message_handler.handle_chat_post_async") as mock_post,
        patch(
            "src.handlers.line.line_message_handler.build_line_messages_from_bot_message",
            return_value=flex_msgs,
        ),
        patch("src.handlers.line.line_message_handler.persist_line_session"),
        patch("src.handlers.line.line_feedback._persist_pending_map"),
    ):
        mock_prime.return_value = MagicMock(get=MagicMock(return_value="ja"))
        asyncio.run(
            _process_text_message(
                "Utest",
                "mrcdevline00000001",
                "reply-tok",
                event={"timestamp": int(time.time() * 1000), "webhookEventId": "evt-preview-1"},
            )
        )

    mock_post.assert_not_called()
    mock_loading.assert_awaited_once()
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
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
    ):
        asyncio.run(
            _deliver_line_messages(
                "Utest",
                flex,
                reply_token="tok",
            )
        )

    mock_push.assert_awaited_once()
    assert len(mock_push.await_args.args[1]) == 1


def test_message_event_ignores_feedback_display_text(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    with patch(
        "src.handlers.line.line_message_handler._process_text_message",
        new_callable=AsyncMock,
    ) as mock_proc:
        asyncio.run(
            _dispatch_event(
                {
                    "type": "message",
                    "replyToken": "tok",
                    "source": {"type": "user", "userId": "U1"},
                    "message": {"type": "text", "text": "役に立った"},
                }
            )
        )
    mock_proc.assert_not_awaited()


def test_process_line_events_handles_postback_before_message(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.line.line_message_handler.LINE_CHANNEL_ACCESS_TOKEN",
        "token",
    )
    order: list[str] = []

    async def track_postback(*_args, **_kwargs):
        order.append("postback")

    async def track_message(*_args, **_kwargs):
        order.append("message")

    with (
        patch(
            "src.handlers.line.line_feedback.handle_line_feedback_postback",
            side_effect=track_postback,
        ),
        patch(
            "src.handlers.line.line_message_handler._process_text_message",
            side_effect=track_message,
        ),
        patch("src.handlers.line.line_reply.acquire_thread_http_client", return_value=MagicMock()),
        patch("src.handlers.line.line_reply.set_http_client"),
    ):
        from src.handlers.line.line_message_handler import process_line_events

        asyncio.run(
            process_line_events(
                [
                    {
                        "type": "message",
                        "source": {"type": "user", "userId": "U1"},
                        "message": {"type": "text", "text": "頭痛"},
                    },
                    {
                        "type": "postback",
                        "source": {"type": "user", "userId": "U1"},
                        "postback": {"data": "mrcfb|pos|abc"},
                    },
                ]
            )
        )
    assert order == ["postback", "message"]


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
