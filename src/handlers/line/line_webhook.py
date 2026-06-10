"""
LINE Webhook 受信（環境構築フェーズ）

署名検証と 200 応答のみ。Reply API・推奨ロジックは未実装。
"""
from __future__ import annotations

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


async def handle_line_webhook(request: Request) -> Response:
    """POST /line/webhook — 署名検証後に 200 を返す（Reply なし）。"""
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

    event_count = 0
    if body:
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                events = payload.get("events")
                if isinstance(events, list):
                    event_count = len(events)
        except json.JSONDecodeError:
            logger.warning("LINE webhook body is not valid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    logger.info("LINE webhook received events=%s", event_count)
    return JSONResponse({"status": "ok", "events_received": event_count})
