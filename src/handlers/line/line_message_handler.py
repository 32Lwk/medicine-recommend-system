"""LINE イベント1件あたりの処理（推奨パイプライン連携）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
from src.handlers.chat_handler import handle_chat_post
from src.handlers.line.flex_messages import build_line_messages_from_bot_message
from src.handlers.line.line_reply import push_messages, reply_messages, start_loading_animation
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
NON_TEXT_HINT = (
    "スタンプ・画像には対応していません。症状はテキストでお送りください。例: 頭が痛い"
)
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


async def _push_message_chunk(user_id: str, messages: list[dict[str, Any]]) -> None:
    """最大5件を1回の Push で送る。失敗時は1件ずつテキストフォールバック。"""
    if not messages:
        return
    if await push_messages(user_id, messages):
        return
    for msg in messages:
        if await push_messages(user_id, [msg]):
            continue
        fallback_text = ""
        if msg.get("type") == "flex":
            fallback_text = str(msg.get("altText") or "").strip()
        elif msg.get("type") == "text":
            fallback_text = str(msg.get("text") or "").strip()
        if not fallback_text:
            fallback_text = GENERIC_SAFE_TEXT
        logger.warning("LINE push failed; sending text fallback userId=%s", user_id)
        await push_messages(user_id, [{"type": "text", "text": fallback_text[:5000]}])


async def _deliver_line_messages(
    user_id: str,
    line_messages: list[dict[str, Any]],
    *,
    reply_token: str | None = None,
    sid: str | None = None,
    user_message: str = "",
    bot_message: dict[str, Any] | None = None,
    lang: str | None = None,
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
    if not messages:
        return

    chunks = [
        messages[i : i + LINE_MAX_MESSAGES_PER_REQUEST]
        for i in range(0, len(messages), LINE_MAX_MESSAGES_PER_REQUEST)
    ]

    if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
        if await reply_messages(reply_token, chunks[0]):
            for chunk in chunks[1:]:
                await _push_message_chunk(user_id, chunk)
            return
        logger.warning("LINE reply failed; falling back to push userId=%s", user_id)

    for chunk in chunks:
        await _push_message_chunk(user_id, chunk)


async def process_line_events(events: list[dict[str, Any]]) -> None:
    from src.handlers.line import line_reply

    # lifespan の httpx クライアントはメインループ専用。バックグラウンドスレッドでは専用クライアントを使う。
    async with httpx.AsyncClient(timeout=60.0) as client:
        line_reply.set_http_client(client)
        try:
            for event in events:
                if not isinstance(event, dict):
                    continue
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
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(reply_token, [{"type": "text", "text": FOLLOW_WELCOME_TEXT}])
        return

    if event_type == "postback":
        user_id = _extract_user_id(event)
        if not user_id:
            return
        postback = event.get("postback")
        data = postback.get("data") if isinstance(postback, dict) else ""
        from src.handlers.line.line_feedback import handle_line_feedback_postback

        await handle_line_feedback_postback(
            user_id,
            str(data or ""),
            reply_token=reply_token,
        )
        return

    if event_type == "unfollow":
        logger.info("LINE unfollow userId=%s", event.get("source", {}).get("userId"))
        return

    if event_type != "message":
        logger.debug("LINE event ignored type=%s", event_type)
        return

    if not _is_one_to_one(event):
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(reply_token, [{"type": "text", "text": GROUP_UNSUPPORTED_TEXT}])
        return

    message = event.get("message")
    if not isinstance(message, dict):
        return

    user_id = _extract_user_id(event)
    if not user_id:
        return

    if message.get("type") != "text":
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(reply_token, [{"type": "text", "text": NON_TEXT_HINT}])
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    await _process_text_message(user_id, text, reply_token)


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
) -> None:
    sid = line_sid(user_id)
    logger.info("LINE text message userId=%s sid=%s text=%s", user_id, sid, text)

    session = prime_line_session(user_id)
    client_info = ChatClientInfo(client_ip="line-webhook", user_agent="LINE-MessagingAPI")

    from src.handlers.line.line_dev_triggers import try_line_dev_flex_preview

    preview_bot = try_line_dev_flex_preview(
        text,
        session,
        sid,
        client_ip=client_info.client_ip,
        user_agent=client_info.user_agent,
    )
    if preview_bot is not None:
        if LINE_CHANNEL_ACCESS_TOKEN:
            line_messages = build_line_messages_from_bot_message(
                preview_bot,
                lang=session.get("detected_language") or "ja",
                session_id=sid,
            )
            await _deliver_line_messages(
                user_id,
                line_messages,
                reply_token=reply_token,
                sid=sid,
                user_message=text,
                bot_message=preview_bot,
                lang=session.get("detected_language") or "ja",
            )
        persist_line_session(sid, session)
        return

    from src.core.language_utils import detect_language
    from src.handlers.line.line_job_lock import LineJobLock
    from src.services.processing_status import mark_processing_step, set_processing_language

    lang = detect_language(text)
    session["detected_language"] = lang

    job_lock = LineJobLock()
    if not job_lock.acquire(sid):
        logger.info("LINE duplicate job skipped sid=%s", sid)
        if LINE_CHANNEL_ACCESS_TOKEN:
            await start_loading_animation(user_id)
        return

    loading_stop = asyncio.Event()
    loading_task = None
    if LINE_CHANNEL_ACCESS_TOKEN:
        await start_loading_animation(user_id)
        from src.handlers.line.line_loading import run_loading_keepalive

        loading_task = asyncio.create_task(run_loading_keepalive(user_id, loading_stop))
    else:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set; skipping loading/push")

    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()

    set_processing_language(sid, lang)
    mark_processing_step(sid, "validate")

    try:
        await asyncio.to_thread(
            handle_chat_post,
            session,
            client_info,
            text,
            sid,
            monitor,
        )
        mark_processing_step(sid, "finalize")

        bot_msg = resolve_latest_bot_message(session, sid)
        if not bot_msg:
            logger.warning("LINE no bot message after pipeline sid=%s", sid)
            if LINE_CHANNEL_ACCESS_TOKEN:
                await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
            return

        line_messages = build_line_messages_from_bot_message(
            bot_msg,
            lang=lang,
            session_id=sid,
        )
        if not LINE_CHANNEL_ACCESS_TOKEN:
            return

        await _deliver_line_messages(
            user_id,
            line_messages,
            reply_token=reply_token,
            sid=sid,
            user_message=text,
            bot_message=bot_msg,
            lang=lang,
        )
    except Exception as exc:
        logger.exception("LINE pipeline error sid=%s", sid)
        if LINE_CHANNEL_ACCESS_TOKEN:
            await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
        _notify_line_error_email(user_id, sid, str(exc))
    finally:
        loading_stop.set()
        if loading_task is not None:
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
        job_lock.release(sid)
        persist_line_session(sid, session)
