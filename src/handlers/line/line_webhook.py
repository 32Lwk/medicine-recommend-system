"""
LINE Webhook 受信

署名検証後に即 200 を返し、イベント処理はバックグラウンドで実行する。
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from config.line_config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    LINE_WEBHOOK_ENABLED,
)
from src.handlers.line.line_dedup import mark_webhook_event_seen
from src.handlers.line.line_message_handler import process_line_events

logger = logging.getLogger(__name__)


def verify_line_signature(body: bytes, channel_secret: str, signature: str | None) -> bool:
    """X-Line-Signature を Channel Secret で検証する。"""
    if not channel_secret or not signature:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def line_webhook_status() -> dict[str, Any]:
    """設定状態（秘密値は返さない）。"""
    return {
        "enabled": LINE_WEBHOOK_ENABLED,
        "channel_secret_configured": bool(LINE_CHANNEL_SECRET),
        "channel_access_token_configured": bool(LINE_CHANNEL_ACCESS_TOKEN),
    }


def _log_task_exception(task: asyncio.Task) -> None:
    try:
        exc = task.exception()
        if exc:
            logger.error("LINE background task failed: %s", exc, exc_info=exc)
    except asyncio.CancelledError:
        pass


def _schedule_line_events(events: list[dict[str, Any]]) -> None:
    filtered: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = event.get("webhookEventId")
        if mark_webhook_event_seen(event_id):
            logger.info("LINE duplicate webhook event skipped id=%s", event_id)
            continue
        filtered.append(event)
    if not filtered:
        return
    task = asyncio.create_task(process_line_events(filtered))
    task.add_done_callback(_log_task_exception)


async def handle_line_webhook(request: Request) -> Response:
    """POST /line/webhook — 署名検証後に 200 を返し、イベントは非同期処理。"""
    if not LINE_WEBHOOK_ENABLED:
        return JSONResponse(
            {"error": "LINE webhook is disabled", "hint": "Set LINE_WEBHOOK_ENABLED=true"},
            status_code=503,
        )

    if not LINE_CHANNEL_SECRET:
        logger.error("LINE webhook enabled but LINE_CHANNEL_SECRET is not set")
        return JSONResponse(
            {"error": "LINE_CHANNEL_SECRET is not configured"},
            status_code=503,
        )

    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    if not verify_line_signature(body, LINE_CHANNEL_SECRET, signature):
        logger.warning("LINE webhook signature verification failed")
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    events: list[dict[str, Any]] = []
    if body:
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                raw_events = payload.get("events")
                if isinstance(raw_events, list):
                    events = [e for e in raw_events if isinstance(e, dict)]
        except json.JSONDecodeError:
            logger.warning("LINE webhook body is not valid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    logger.info("LINE webhook received events=%s", len(events))
    if events:
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.warning(
                "LINE_CHANNEL_ACCESS_TOKEN not configured; events accepted but reply/push disabled"
            )
        _schedule_line_events(events)

    return JSONResponse({"status": "ok", "events_received": len(events)})
