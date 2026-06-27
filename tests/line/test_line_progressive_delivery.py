"""LINE 段階配信（carousel Push → advice Reply）のテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.line_progressive_delivery import (
    LineDeliveryContext,
    bind_carousel_flush_to_event_loop,
    build_advice_only_line_messages,
    deliver_final_line_messages,
    push_carousel_if_eligible,
    set_line_delivery_context,
    should_use_progressive_delivery,
)


def test_should_use_progressive_delivery_physical_line_only():
    sid = "line:U123"
    triage = {"category": "Physical"}
    meds = [{"product_name": "テスト薬"}]
    assert should_use_progressive_delivery(sid, triage, meds) is True
    assert should_use_progressive_delivery("web:abc", triage, meds) is False
    assert should_use_progressive_delivery(sid, {"category": "Other"}, meds) is False


def test_build_advice_only_line_messages_single_bubble():
    bot = {
        "diagnosis": {
            "medicine_type": "解熱鎮痛薬",
            "recommended_medicines": [
                {
                    "product_name": "テスト薬",
                    "explanation": "おすすめです。",
                }
            ],
        }
    }
    msgs = build_advice_only_line_messages(bot, lang="ja")
    assert len(msgs) == 1
    assert msgs[0]["type"] == "flex"


def test_deliver_final_uses_reply_when_carousel_sent():
    ctx = LineDeliveryContext(
        user_id="U1",
        reply_token="tok",
        lang="ja",
        sid="line:U1",
        use_progressive=True,
        carousel_sent=True,
        carousel_failed=False,
        event_timestamp_ms=int(__import__("time").time() * 1000),
    )
    set_line_delivery_context(ctx)
    bot = {
        "diagnosis": {
            "medicine_type": "解熱鎮痛薬",
            "recommended_medicines": [{"product_name": "A", "explanation": "x"}],
        }
    }
    deliver_all = AsyncMock()
    reply_fn = AsyncMock(return_value=True)
    push_chunk = AsyncMock()

    with (
        patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token"),
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
    ):
        try:
            asyncio.run(
                deliver_final_line_messages(
                    "U1",
                    [{"type": "flex", "altText": "full"}],
                    reply_token="tok",
                    sid="line:U1",
                    user_message="頭痛",
                    bot_message=bot,
                    lang="ja",
                    push_chunk_fn=push_chunk,
                    reply_fn=reply_fn,
                    deliver_all_fn=deliver_all,
                )
            )
        finally:
            set_line_delivery_context(None)

    reply_fn.assert_awaited_once()
    deliver_all.assert_not_awaited()


def test_deliver_final_push_fallback_does_not_call_deliver_all():
    """Reply 失敗後の Push 成功時に full bundle を二重送信しない。"""
    ctx = LineDeliveryContext(
        user_id="U1",
        reply_token="tok",
        lang="ja",
        sid="line:U1",
        use_progressive=True,
        carousel_sent=True,
        carousel_failed=False,
        event_timestamp_ms=int(__import__("time").time() * 1000),
    )
    set_line_delivery_context(ctx)
    bot = {
        "diagnosis": {
            "medicine_type": "解熱鎮痛薬",
            "recommended_medicines": [{"product_name": "A", "explanation": "x"}],
        }
    }
    deliver_all = AsyncMock()
    reply_fn = AsyncMock(return_value=False)
    push_chunk = AsyncMock(return_value=True)

    with (
        patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token"),
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
    ):
        try:
            asyncio.run(
                deliver_final_line_messages(
                    "U1",
                    [{"type": "flex", "altText": "full"}],
                    reply_token="tok",
                    sid="line:U1",
                    user_message="頭痛",
                    bot_message=bot,
                    lang="ja",
                    push_chunk_fn=push_chunk,
                    reply_fn=reply_fn,
                    deliver_all_fn=deliver_all,
                )
            )
        finally:
            set_line_delivery_context(None)

    reply_fn.assert_awaited_once()
    push_chunk.assert_awaited_once()
    deliver_all.assert_not_awaited()


def test_push_carousel_if_eligible_sets_context():
    ctx = LineDeliveryContext(user_id="U1", reply_token="tok", lang="ja", sid="line:U1")
    set_line_delivery_context(ctx)
    rec = {"recommended_medicines": [{"product_name": "A", "explanation": "x"}]}
    triage = {"category": "Physical"}

    with (
        patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token"),
        patch(
            "src.handlers.line.line_reply.push_messages",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "src.handlers.line.flex_messages.build_recommendation_carousel",
            return_value={"type": "flex", "altText": "c", "contents": {}},
        ),
    ):
        asyncio.run(
            push_carousel_if_eligible(
                sid="line:U1",
                triage_result=triage,
                recommendation_result=rec,
                lang="ja",
            )
        )

    assert ctx.use_progressive is True
    assert ctx.carousel_sent is True
    set_line_delivery_context(None)


def test_deliver_final_falls_back_when_carousel_failed():
    ctx = LineDeliveryContext(
        user_id="U1",
        reply_token="tok",
        lang="ja",
        sid="line:U1",
        use_progressive=True,
        carousel_sent=False,
        carousel_failed=True,
    )
    set_line_delivery_context(ctx)
    deliver_all = AsyncMock()

    with patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token"):
        try:
            asyncio.run(
                deliver_final_line_messages(
                    "U1",
                    [{"type": "flex", "altText": "full"}],
                    reply_token="tok",
                    sid="line:U1",
                    user_message="頭痛",
                    bot_message={"diagnosis": {"recommended_medicines": [{"product_name": "A"}]}},
                    lang="ja",
                    push_chunk_fn=AsyncMock(),
                    reply_fn=AsyncMock(return_value=True),
                    deliver_all_fn=deliver_all,
                )
            )
        finally:
            set_line_delivery_context(None)

    deliver_all.assert_awaited_once()


def test_deliver_final_after_carousel_flush_timeout_skips_full_bundle():
    """carousel Push 済み + flush タイムアウト時は advice のみ（full bundle 再送しない）。"""
    ctx = LineDeliveryContext(
        user_id="U1",
        reply_token="tok",
        lang="ja",
        sid="line:U1",
        use_progressive=True,
        carousel_sent=True,
        carousel_failed=True,
        event_timestamp_ms=int(__import__("time").time() * 1000),
    )
    set_line_delivery_context(ctx)
    bot = {
        "diagnosis": {
            "medicine_type": "解熱鎮痛薬",
            "recommended_medicines": [{"product_name": "A", "explanation": "x"}],
        }
    }
    deliver_all = AsyncMock()
    reply_fn = AsyncMock(return_value=True)
    push_chunk = AsyncMock()

    with (
        patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token"),
        patch("src.handlers.line.line_delivery.get_line_channel_access_token", return_value="token"),
    ):
        try:
            asyncio.run(
                deliver_final_line_messages(
                    "U1",
                    [{"type": "flex", "altText": "full"}],
                    reply_token="tok",
                    sid="line:U1",
                    user_message="頭痛",
                    bot_message=bot,
                    lang="ja",
                    push_chunk_fn=push_chunk,
                    reply_fn=reply_fn,
                    deliver_all_fn=deliver_all,
                )
            )
        finally:
            set_line_delivery_context(None)

    reply_fn.assert_awaited_once()
    deliver_all.assert_not_awaited()


def test_schedule_carousel_push_uses_flush_when_bound():
    ctx = LineDeliveryContext(user_id="U1", reply_token="tok", lang="ja", sid="line:U1")
    calls: list[dict] = []

    def _flush(payload: dict) -> None:
        calls.append(payload)

    ctx.carousel_flush = _flush
    set_line_delivery_context(ctx)
    rec = {"recommended_medicines": [{"product_name": "A"}]}
    triage = {"category": "Physical"}

    from src.handlers.line.line_progressive_delivery import schedule_carousel_push_for_line

    schedule_carousel_push_for_line(
        sid="line:U1",
        triage_result=triage,
        recommendation_result=rec,
        lang="ja",
    )
    set_line_delivery_context(None)
    assert len(calls) == 1
    assert calls[0]["sid"] == "line:U1"


def test_non_physical_uses_full_bundle_not_progressive():
    assert should_use_progressive_delivery(
        "line:U1",
        {"category": "Emotional"},
        [{"product_name": "A"}],
    ) is False


def test_carousel_flush_timeout_marks_failed():
    ctx = LineDeliveryContext(user_id="U1", reply_token="tok", lang="ja", sid="line:U1")
    set_line_delivery_context(ctx)
    loop = asyncio.new_event_loop()

    async def _slow_push(**_kwargs):
        await asyncio.sleep(10)

    bind_carousel_flush_to_event_loop(ctx, loop)
    try:
        with (
            patch(
                "src.handlers.line.line_progressive_delivery.push_carousel_if_eligible",
                side_effect=_slow_push,
            ),
            patch(
                "src.handlers.line.line_progressive_delivery.CAROUSEL_FLUSH_TIMEOUT_SEC",
                0.1,
            ),
        ):
            ctx.carousel_flush(
                {
                    "sid": "line:U1",
                    "triage_result": {"category": "Physical"},
                    "recommendation_result": {"recommended_medicines": [{"product_name": "A"}]},
                    "lang": "ja",
                }
            )
        assert ctx.carousel_failed is True
    finally:
        set_line_delivery_context(None)
        loop.close()
