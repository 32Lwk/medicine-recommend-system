"""LINE イベント1件あたりの処理（推奨パイプライン連携）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
from src.handlers.chat_handler import handle_chat_post_async
from src.handlers.line.flex_messages import build_line_messages_from_bot_message
from src.handlers.line.line_progressive_delivery import (
    LineDeliveryContext,
    bind_carousel_flush_to_event_loop,
    deliver_final_line_messages,
    set_line_delivery_context,
)
from src.handlers.line.line_dedup import extract_webhook_dedup_key
from src.handlers.line.line_delivery import deliver_line_messages
from src.handlers.line.line_loading import begin_line_loading, end_line_loading
from src.handlers.line.line_reply import push_messages, reply_messages
from src.handlers.line.line_session import (
    line_sid,
    persist_line_session,
    prime_line_session,
    resolve_latest_bot_message,
)
from src.services.budget_guard import _send_email, get_alert_email
from src.utils.chat_http_context import ChatClientInfo
from src.utils.performance_monitor import get_global_monitor

logger = logging.getLogger(__name__)

GENERIC_SAFE_TEXT = (
    "処理中に問題が発生しました。しばらくして再送するか、薬剤師にご相談ください。"
)
GROUP_UNSUPPORTED_TEXT = "現在は個人チャットのみ対応しています。"
FOLLOW_WELCOME_TEXT = (
    "友だち追加ありがとうございます。"
    "お困りの症状をテキストでお知らせいただければ、お薬の候補をご提案します。"
)


def _notify_line_error_email(user_id: str, sid: str, detail: str) -> None:
    email = get_alert_email()
    if not email:
        logger.info("LINE error email skipped (no alert_email)")
        return
    subject = "[medicine-recommend] LINE ハンドラエラー"
    body = f"userId: {user_id}\nsid: {sid}\n{detail}\n"
    if not _send_email(email, subject, body):
        logger.warning("LINE error email not sent (SMTP)")


LINE_MAX_MESSAGES_PER_REQUEST = 5


from src.handlers.line.line_timestamp import line_event_timestamp_ms as _event_timestamp_ms


async def _dispatch_quick_text_reply(
    user_id: str | None,
    reply_token: str | None,
    text: str,
    event: dict[str, Any],
) -> None:
    """follow / 非テキスト等の即時応答。Reply 優先・失敗時 Push。"""
    if not user_id or not LINE_CHANNEL_ACCESS_TOKEN:
        return
    await deliver_line_messages(
        user_id,
        [{"type": "text", "text": text}],
        reply_token=reply_token,
        reply_fn=reply_messages,
        push_chunk_fn=_push_message_chunk,
        event_timestamp_ms=_event_timestamp_ms(event),
    )


async def _push_message_chunk(user_id: str, messages: list[dict[str, Any]]) -> bool:
    """最大5件を1回の Push で送る。失敗時は1件ずつテキストフォールバック。"""
    if not messages:
        return False
    if await push_messages(user_id, messages):
        return True
    delivered = False
    for msg in messages:
        if await push_messages(user_id, [msg]):
            delivered = True
            continue
        fallback_text = ""
        if msg.get("type") == "flex":
            fallback_text = str(msg.get("altText") or "").strip()
        elif msg.get("type") == "text":
            fallback_text = str(msg.get("text") or "").strip()
        if not fallback_text:
            fallback_text = GENERIC_SAFE_TEXT
        logger.warning("LINE push failed; sending text fallback userId=%s", user_id)
        if await push_messages(user_id, [{"type": "text", "text": fallback_text[:5000]}]):
            delivered = True
    return delivered


async def _deliver_line_messages(
    user_id: str,
    line_messages: list[dict[str, Any]],
    *,
    reply_token: str | None = None,
    sid: str | None = None,
    user_message: str = "",
    bot_message: dict[str, Any] | None = None,
    lang: str | None = None,
    force_delivery: bool = False,
) -> None:
    """Reply（可能なら）または Push で応答。1リクエストあたり最大5件まとめて送る。"""
    messages = line_messages
    if sid and bot_message is not None:
        from src.handlers.line.line_feedback import prepare_line_messages_with_feedback

        messages = prepare_line_messages_with_feedback(
            line_messages,
            sid=sid,
            user_message=user_message,
            bot_message=bot_message,
            lang=lang,
        )
    if sid:
        from src.handlers.line.line_quick_actions import attach_session_quick_actions
        from src.services.session_manager import resolve_session_snapshot

        session_data = resolve_session_snapshot(sid) or {}
        messages = attach_session_quick_actions(messages, session_data, lang=lang)
    if not messages:
        return

    from src.handlers.line.line_progressive_delivery import get_line_delivery_context

    delivery_ctx = get_line_delivery_context()
    event_ts = delivery_ctx.event_timestamp_ms if delivery_ctx else None

    await deliver_line_messages(
        user_id,
        messages,
        reply_token=reply_token,
        reply_fn=reply_messages,
        push_chunk_fn=_push_message_chunk,
        force=force_delivery,
        event_timestamp_ms=event_ts,
        bot_message=bot_message,
    )


async def process_line_events(events: list[dict[str, Any]]) -> None:
    from src.handlers.line import line_reply

    # lifespan の httpx クライアントはメインループ専用。バックグラウンドスレッドでは再利用クライアントを使う。
    client = line_reply.acquire_thread_http_client()
    line_reply.set_http_client(client)
    try:
        ordered = sorted(
            (e for e in events if isinstance(e, dict)),
            key=lambda ev: 0 if ev.get("type") == "postback" else 1,
        )
        for event in ordered:
            try:
                await _dispatch_event(event)
            except Exception:
                logger.exception("LINE event handler error type=%s", event.get("type"))
                user_id = _extract_user_id(event)
                if user_id and LINE_CHANNEL_ACCESS_TOKEN:
                    await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
                    _notify_line_error_email(user_id, line_sid(user_id), "unhandled event exception")
    finally:
        line_reply.set_http_client(None)


async def _dispatch_event(event: dict[str, Any]) -> None:
    event_type = event.get("type")
    reply_token = event.get("replyToken")

    if event_type == "follow":
        user_id = _extract_user_id(event)
        if user_id:
            from src.handlers.line.line_profile import ensure_line_user_profile
            from src.handlers.line.line_session import prime_line_session

            sid = line_sid(user_id)
            session = prime_line_session(user_id)
            await ensure_line_user_profile(user_id, session, sid=sid)
            from src.handlers.line.line_session import persist_line_session

            persist_line_session(sid, session)
            await _dispatch_quick_text_reply(user_id, reply_token, FOLLOW_WELCOME_TEXT, event)
        return

    if event_type == "postback":
        user_id = _extract_user_id(event)
        if not user_id:
            return
        postback = event.get("postback")
        data = postback.get("data") if isinstance(postback, dict) else ""
        data_str = str(data or "")

        delivery_ctx = LineDeliveryContext(
            user_id=user_id,
            reply_token=reply_token,
            lang="ja",
            sid=line_sid(user_id),
            event_timestamp_ms=_event_timestamp_ms(event),
        )
        set_line_delivery_context(delivery_ctx)
        try:
            from src.handlers.line.line_menu_actions import handle_line_menu_postback

            if await handle_line_menu_postback(user_id, data_str, reply_token=reply_token):
                return

            from src.handlers.line.line_feedback import handle_line_feedback_postback

            await handle_line_feedback_postback(
                user_id,
                data_str,
                reply_token=reply_token,
            )
        finally:
            set_line_delivery_context(None)
        return

    if event_type == "unfollow":
        logger.info("LINE unfollow userId=%s", event.get("source", {}).get("userId"))
        return

    if event_type != "message":
        logger.debug("LINE event ignored type=%s", event_type)
        return

    if not _is_one_to_one(event):
        user_id = _extract_user_id(event)
        await _dispatch_quick_text_reply(user_id, reply_token, GROUP_UNSUPPORTED_TEXT, event)
        return

    message = event.get("message")
    if not isinstance(message, dict):
        return

    user_id = _extract_user_id(event)
    if not user_id:
        return

    msg_type = message.get("type")
    if msg_type == "sticker":
        from src.handlers.line.line_non_text import (
            STICKER_UNSUPPORTED_REPLY,
            try_resolve_sticker_as_text,
        )

        synthetic = try_resolve_sticker_as_text(message)
        if synthetic:
            logger.info(
                "LINE sticker resolved as text userId=%s packageId=%s stickerId=%s text=%s",
                user_id,
                message.get("packageId"),
                message.get("stickerId"),
                synthetic,
            )
            await _process_text_message(user_id, synthetic, reply_token, event=event)
            return
        await _dispatch_quick_text_reply(
            user_id,
            reply_token,
            STICKER_UNSUPPORTED_REPLY,
            event,
        )
        return

    if msg_type != "text":
        from src.handlers.line.line_non_text import build_non_text_reply

        await _dispatch_quick_text_reply(
            user_id,
            reply_token,
            build_non_text_reply(str(msg_type or "")),
            event,
        )
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    from src.handlers.line.line_feedback import is_line_feedback_display_text
    from src.handlers.line.line_menu_actions import is_line_menu_display_text

    if is_line_feedback_display_text(text) or is_line_menu_display_text(text):
        logger.info(
            "LINE feedback displayText echo ignored userId=%s text=%s",
            user_id,
            text,
        )
        return

    await _process_text_message(user_id, text, reply_token, event=event)


def _is_one_to_one(event: dict[str, Any]) -> bool:
    source = event.get("source") or {}
    return source.get("type") == "user" and bool(source.get("userId"))


def _extract_user_id(event: dict[str, Any]) -> str | None:
    source = event.get("source") or {}
    if source.get("type") == "user":
        return source.get("userId")
    return source.get("userId")


async def _process_text_message(
    user_id: str,
    text: str,
    reply_token: str | None,
    *,
    event: dict[str, Any] | None = None,
) -> None:
    sid = line_sid(user_id)
    logger.info("LINE text message userId=%s sid=%s text=%s", user_id, sid, text)

    from src.services.pipeline_perf import log_pipeline_perf, mark_pipeline_step

    dedup_key = extract_webhook_dedup_key(event) if event else None
    event_timestamp_ms = _event_timestamp_ms(event) if event else None

    delivery_ctx = LineDeliveryContext(
        user_id=user_id,
        reply_token=reply_token,
        lang="ja",
        sid=sid,
        dedup_key=dedup_key,
        event_timestamp_ms=event_timestamp_ms,
    )
    set_line_delivery_context(delivery_ctx)

    loading_stop = asyncio.Event()
    loading_keepalive = None
    job_lock = None

    try:
        session = prime_line_session(user_id)
        client_info = ChatClientInfo(client_ip="line-webhook", user_agent="LINE-MessagingAPI")

        from src.handlers.line.line_profile import ensure_line_user_profile
        from src.core.language_utils import (
            resolve_session_language,
            update_session_language_from_message,
        )

        await ensure_line_user_profile(user_id, session, sid=sid)
        delivery_ctx.lang = resolve_session_language(session)

        from src.handlers.line.line_dev_triggers import try_line_dev_flex_preview

        preview_bot = try_line_dev_flex_preview(
            text,
            session,
            sid,
            client_ip=client_info.client_ip,
            user_agent=client_info.user_agent,
        )
        if preview_bot is not None:
            loading_stop, loading_keepalive = await begin_line_loading(user_id)
            preview_lang = update_session_language_from_message(session, text)
            if LINE_CHANNEL_ACCESS_TOKEN:
                line_messages = build_line_messages_from_bot_message(
                    preview_bot,
                    lang=preview_lang,
                    session_id=sid,
                )
                await _deliver_line_messages(
                    user_id,
                    line_messages,
                    reply_token=reply_token,
                    sid=sid,
                    user_message=text,
                    bot_message=preview_bot,
                    lang=preview_lang,
                )
            persist_line_session(sid, session)
            return

        from src.handlers.line.line_job_lock import LineJobLock
        from src.services.processing_status import mark_processing_step, set_processing_language

        lang = update_session_language_from_message(session, text)
        delivery_ctx.lang = lang

        job_lock = LineJobLock()
        if not job_lock.acquire(sid):
            logger.info("LINE duplicate job skipped sid=%s", sid)
            return

        from src.services.pipeline_perf import bind_pipeline_perf

        bind_pipeline_perf(sid=sid, channel="line")

        loading_stop, loading_keepalive = await begin_line_loading(user_id)
        mark_pipeline_step("line_loading_start")

        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set; skipping loading/push")

        monitor = get_global_monitor()
        monitor.start_monitoring()
        monitor.increment_request()

        set_processing_language(sid, lang)
        mark_processing_step(sid, "validate")

        loop = asyncio.get_running_loop()
        bind_carousel_flush_to_event_loop(delivery_ctx, loop)

        try:
            await handle_chat_post_async(
                session,
                client_info,
                text,
                sid,
                monitor,
            )
            mark_processing_step(sid, "finalize")

            from src.handlers.line.line_profile import ensure_line_user_profile

            await ensure_line_user_profile(user_id, session, sid=sid)

            bot_msg = resolve_latest_bot_message(session, sid)
            if not bot_msg:
                logger.warning("LINE no bot message after pipeline sid=%s", sid)
                if LINE_CHANNEL_ACCESS_TOKEN:
                    await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
                return

            from src.services.counseling.counseling_logger import maybe_log_line_turn_counseling_detail

            maybe_log_line_turn_counseling_detail(session, sid, text, bot_msg)

            line_messages = build_line_messages_from_bot_message(
                bot_msg,
                lang=lang,
                session_id=sid,
            )
            if not LINE_CHANNEL_ACCESS_TOKEN:
                return

            await deliver_final_line_messages(
                user_id,
                line_messages,
                reply_token=reply_token,
                sid=sid,
                user_message=text,
                bot_message=bot_msg,
                lang=lang,
                push_chunk_fn=_push_message_chunk,
                reply_fn=reply_messages,
                deliver_all_fn=_deliver_line_messages,
            )
            mark_pipeline_step("line_reply_done")
        except Exception as exc:
            logger.exception("LINE pipeline error sid=%s", sid)
            if LINE_CHANNEL_ACCESS_TOKEN:
                await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
            _notify_line_error_email(user_id, sid, str(exc))
        finally:
            if job_lock is not None:
                job_lock.release(sid)
            persist_line_session(sid, session)
            from src.services.processing_status import clear_processing_status

            clear_processing_status(sid)
    finally:
        await end_line_loading(loading_stop, loading_keepalive)
        log_pipeline_perf(sid=sid)
        set_line_delivery_context(None)
