"""LINE イベント1件あたりの処理（推奨パイプライン連携）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
from src.handlers.chat_handler import handle_chat_post
from src.handlers.line.flex_messages import build_line_messages_from_bot_message
from src.handlers.line.line_reply import push_messages, reply_messages
from src.handlers.line.line_session import (
    get_latest_bot_message,
    line_sid,
    persist_line_session,
    prime_line_session,
)
from src.services.budget_guard import _send_email, get_alert_email
from src.utils.chat_http_context import ChatClientInfo
from src.utils.performance_monitor import get_global_monitor

logger = logging.getLogger(__name__)

CONFIRMING_TEXT = "症状を確認しています。少々お待ちください。"
GENERIC_SAFE_TEXT = (
    "処理中に問題が発生しました。しばらくして再送するか、薬剤師にご相談ください。"
)
PROCESSING_WAIT_TEXT = "現在処理中です。完了後に再度お送りください。"
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


async def process_line_events(events: list[dict[str, Any]]) -> None:
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


async def _dispatch_event(event: dict[str, Any]) -> None:
    event_type = event.get("type")
    reply_token = event.get("replyToken")

    if event_type == "follow":
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(reply_token, [{"type": "text", "text": FOLLOW_WELCOME_TEXT}])
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

    if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
        await reply_messages(reply_token, [{"type": "text", "text": CONFIRMING_TEXT}])
    elif not LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set; skipping reply/push")

    session = prime_line_session(user_id)
    client_info = ChatClientInfo(client_ip="line-webhook", user_agent="LINE-MessagingAPI")
    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()

    from src.core.language_utils import detect_language
    from src.services.chat_inflight import is_chat_job_in_flight
    from src.services.processing_status import mark_processing_step, set_processing_language

    if is_chat_job_in_flight(sid):
        if LINE_CHANNEL_ACCESS_TOKEN:
            await push_messages(user_id, [{"type": "text", "text": PROCESSING_WAIT_TEXT}])
        return

    set_processing_language(sid, detect_language(text))
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

        bot_msg = get_latest_bot_message(sid)
        if not bot_msg:
            logger.warning("LINE no bot message after pipeline sid=%s", sid)
            if LINE_CHANNEL_ACCESS_TOKEN:
                await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
            return

        lang = session.get("detected_language") or "ja"
        line_messages = build_line_messages_from_bot_message(
            bot_msg,
            lang=lang,
            session_id=sid,
        )
        if not LINE_CHANNEL_ACCESS_TOKEN:
            return

        for msg in line_messages:
            await push_messages(user_id, [msg])
    except Exception as exc:
        logger.exception("LINE pipeline error sid=%s", sid)
        if LINE_CHANNEL_ACCESS_TOKEN:
            await push_messages(user_id, [{"type": "text", "text": GENERIC_SAFE_TEXT}])
        _notify_line_error_email(user_id, sid, str(exc))
    finally:
        persist_line_session(sid, session)
