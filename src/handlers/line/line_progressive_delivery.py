"""LINE Physical 推奨の段階配信（Push carousel → Reply advice+feedback）。"""
from __future__ import annotations

import asyncio
import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

CAROUSEL_FLUSH_TIMEOUT_SEC = 3.0

_line_ctx: ContextVar["LineDeliveryContext | None"] = ContextVar("line_delivery_ctx", default=None)

DeliverAllFn = Callable[..., Awaitable[None]]
PushChunkFn = Callable[[str, list[dict[str, Any]]], Awaitable[None]]
ReplyFn = Callable[[str, list[dict[str, Any]]], Awaitable[bool]]
CarouselFlushFn = Callable[[dict[str, Any]], None]


@dataclass
class LineDeliveryContext:
    user_id: str
    reply_token: str | None
    lang: str
    sid: str
    triage_category: str | None = None
    carousel_sent: bool = False
    carousel_failed: bool = False
    use_progressive: bool = False
    carousel_flush: CarouselFlushFn | None = field(default=None, repr=False)


def set_line_delivery_context(ctx: LineDeliveryContext | None) -> None:
    _line_ctx.set(ctx)


def get_line_delivery_context() -> LineDeliveryContext | None:
    return _line_ctx.get()


def should_use_progressive_delivery(
    sid: str | None,
    triage_result: dict[str, Any] | None,
    medicines: list[dict[str, Any]] | None,
) -> bool:
    from src.handlers.line.line_session import is_line_session_id

    if not sid or not is_line_session_id(sid):
        return False
    if not medicines:
        return False
    category = (triage_result or {}).get("category")
    return category == "Physical"


def register_triage_for_line(sid: str | None, triage_result: dict[str, Any] | None) -> None:
    ctx = get_line_delivery_context()
    if ctx is None or not sid or ctx.sid != sid:
        return
    ctx.triage_category = (triage_result or {}).get("category")


def build_carousel_message(
    recommendation_result: dict[str, Any],
    *,
    lang: str,
) -> dict[str, Any] | None:
    """`flex_messages.build_recommendation_carousel` のラッパ。"""
    from src.handlers.line.flex_messages import build_recommendation_carousel, get_line_ui_strings

    medicines = recommendation_result.get("recommended_medicines") or []
    if not medicines:
        return None
    ui = get_line_ui_strings(lang)
    return build_recommendation_carousel(medicines, ui)


def bind_carousel_flush_to_event_loop(ctx: LineDeliveryContext, loop: asyncio.AbstractEventLoop) -> None:
    """sync ワーカーから main event loop へ carousel Push を委譲（asyncio.run 不使用）。"""

    def _flush(payload: dict[str, Any]) -> None:
        fut = asyncio.run_coroutine_threadsafe(
            push_carousel_if_eligible(
                sid=payload.get("sid"),
                triage_result=payload.get("triage_result"),
                recommendation_result=payload.get("recommendation_result") or {},
                lang=str(payload.get("lang") or "ja"),
            ),
            loop,
        )
        try:
            fut.result(timeout=CAROUSEL_FLUSH_TIMEOUT_SEC)
        except TimeoutError:
            logger.warning(
                "LINE carousel push timed out after %.0fs; will include in final reply",
                CAROUSEL_FLUSH_TIMEOUT_SEC,
            )
            ctx = get_line_delivery_context()
            if ctx is not None:
                ctx.carousel_failed = True
        except Exception:
            logger.exception("LINE progressive carousel flush failed")
            ctx = get_line_delivery_context()
            if ctx is not None:
                ctx.carousel_failed = True

    ctx.carousel_flush = _flush


def schedule_carousel_push_for_line(
    *,
    sid: str | None,
    triage_result: dict[str, Any] | None,
    recommendation_result: dict[str, Any],
    lang: str,
) -> None:
    """
    rule_based 成功直後（sync パイプライン）: eligible なら carousel Push。
    LINE handler が event loop を bind 済みなら await 直呼び相当、未設定時は sync フォールバック。
    """
    medicines = recommendation_result.get("recommended_medicines") or []
    if not should_use_progressive_delivery(sid, triage_result, medicines):
        return

    payload = {
        "sid": sid,
        "triage_result": triage_result,
        "recommendation_result": recommendation_result,
        "lang": lang,
    }
    ctx = get_line_delivery_context()
    if ctx is not None and ctx.carousel_flush is not None:
        try:
            ctx.carousel_flush(payload)
        except Exception:
            logger.exception("LINE progressive carousel flush failed sid=%s", sid)
        return

    push_carousel_if_eligible_sync(
        sid=sid,
        triage_result=triage_result,
        recommendation_result=recommendation_result,
        lang=lang,
    )


async def push_carousel_if_eligible(
    *,
    sid: str | None,
    triage_result: dict[str, Any] | None,
    recommendation_result: dict[str, Any],
    lang: str,
) -> None:
    """rule_based 成功直後: carousel Flex を Push（Physical LINE のみ）。"""
    from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
    from src.handlers.line.line_reply import push_messages

    ctx = get_line_delivery_context()
    if ctx is None or not LINE_CHANNEL_ACCESS_TOKEN:
        return

    medicines = recommendation_result.get("recommended_medicines") or []
    if not should_use_progressive_delivery(sid, triage_result, medicines):
        return

    ctx.use_progressive = True
    carousel = build_carousel_message(recommendation_result, lang=lang)
    if carousel is None:
        return
    ok = await push_messages(ctx.user_id, [carousel])
    ctx.carousel_sent = ok
    ctx.carousel_failed = not ok
    if ok:
        logger.info("LINE progressive carousel pushed userId=%s sid=%s", ctx.user_id, sid)
    else:
        logger.warning("LINE progressive carousel push failed userId=%s sid=%s", ctx.user_id, sid)


def build_advice_only_line_messages(
    bot_message: dict[str, Any],
    *,
    lang: str | None,
) -> list[dict[str, Any]]:
    """carousel 送信済み時: advice bubble のみ。"""
    from src.handlers.line.flex_messages import (
        build_advice_bubble,
        build_advice_bullets,
        format_intro,
        get_line_ui_strings,
        truncate_text,
    )

    ui = get_line_ui_strings(lang)
    diagnosis = bot_message.get("diagnosis") if isinstance(bot_message.get("diagnosis"), dict) else {}
    medicines = [
        m for m in (diagnosis.get("recommended_medicines") or []) if isinstance(m, dict)
    ]
    if not medicines:
        return []

    medicine_type = str(diagnosis.get("medicine_type") or "OTC医薬品")
    intro = format_intro(ui, medicine_type=medicine_type, count=len(medicines[:3]))
    bullets = build_advice_bullets(medicines, ui)
    advice_footer = ui.get("footer_caution", "")
    if diagnosis.get("doctor_consultation"):
        advice_footer = f"{advice_footer}\n{truncate_text(diagnosis.get('doctor_consultation'), 200)}"
    advice = build_advice_bubble(intro=intro, bullets=bullets, footer_note=advice_footer, ui=ui)
    return [advice]


def build_final_line_messages(
    bot_message: dict[str, Any],
    *,
    sid: str | None,
    user_message: str,
    lang: str | None,
) -> list[dict[str, Any]]:
    """advice bubble + line_feedback（progressive Reply 用）。"""
    from src.handlers.line.line_feedback import prepare_line_messages_with_feedback

    advice_msgs = build_advice_only_line_messages(bot_message, lang=lang)
    if not advice_msgs:
        return []
    return prepare_line_messages_with_feedback(
        advice_msgs,
        sid=sid or "",
        user_message=user_message,
        bot_message=bot_message,
        lang=lang,
    )


async def deliver_final_line_messages(
    user_id: str,
    line_messages: list[dict[str, Any]],
    *,
    reply_token: str | None,
    sid: str | None,
    user_message: str,
    bot_message: dict[str, Any] | None,
    lang: str | None,
    push_chunk_fn: PushChunkFn,
    reply_fn: ReplyFn,
    deliver_all_fn: DeliverAllFn,
) -> None:
    """
    progressive モード: advice+feedback を Reply 優先。
    carousel 未送/失敗時は従来の一括 Flex 2通へフォールバック。
    """
    from config.line_config import LINE_CHANNEL_ACCESS_TOKEN

    ctx = get_line_delivery_context()
    if (
        ctx is None
        or not ctx.use_progressive
        or ctx.carousel_failed
        or not ctx.carousel_sent
    ):
        await deliver_all_fn(
            user_id,
            line_messages,
            reply_token=reply_token,
            sid=sid,
            user_message=user_message,
            bot_message=bot_message,
            lang=lang,
        )
        return

    if not bot_message or not LINE_CHANNEL_ACCESS_TOKEN:
        return

    messages = build_final_line_messages(
        bot_message,
        sid=sid or ctx.sid,
        user_message=user_message,
        lang=lang,
    )
    if not messages:
        await deliver_all_fn(
            user_id,
            line_messages,
            reply_token=reply_token,
            sid=sid,
            user_message=user_message,
            bot_message=bot_message,
            lang=lang,
        )
        return

    token = reply_token or ctx.reply_token
    if token and await reply_fn(token, messages):
        logger.info("LINE progressive advice+feedback via reply userId=%s", user_id)
        return

    logger.warning("LINE progressive reply failed; push fallback userId=%s", user_id)
    if await push_chunk_fn(user_id, messages):
        return

    logger.warning("LINE progressive push fallback failed; full bundle userId=%s", user_id)
    await deliver_all_fn(
        user_id,
        line_messages,
        reply_token=reply_token,
        sid=sid,
        user_message=user_message,
        bot_message=bot_message,
        lang=lang,
    )


def push_carousel_if_eligible_sync(
    *,
    sid: str | None,
    triage_result: dict[str, Any] | None,
    recommendation_result: dict[str, Any],
    lang: str,
) -> None:
    """sync パイプライン（to_thread）から carousel Push を実行。"""
    import asyncio

    try:
        asyncio.run(
            push_carousel_if_eligible(
                sid=sid,
                triage_result=triage_result,
                recommendation_result=recommendation_result,
                lang=lang,
            )
        )
    except Exception:
        logger.exception("LINE progressive carousel sync push failed sid=%s", sid)
