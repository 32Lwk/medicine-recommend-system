"""LINE Messaging API Reply / Push クライアント。"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN

logger = logging.getLogger(__name__)

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

_http_client: httpx.AsyncClient | None = None


def set_http_client(client: httpx.AsyncClient | None) -> None:
    global _http_client
    _http_client = client


def _headers() -> dict[str, str] | None:
    token = LINE_CHANNEL_ACCESS_TOKEN
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def _post_json(url: str, payload: dict[str, Any], *, log_label: str) -> bool:
    hdrs = _headers()
    if not hdrs:
        logger.warning("LINE %s skipped: LINE_CHANNEL_ACCESS_TOKEN not configured", log_label)
        return False

    client = _http_client
    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        own_client = True
    try:
        response = await client.post(url, headers=hdrs, json=payload)
        if response.status_code >= 400:
            logger.warning(
                "LINE %s failed status=%s body=%s",
                log_label,
                response.status_code,
                (response.text or "")[:500],
            )
            return False
        logger.info("LINE %s ok", log_label)
        return True
    except Exception:
        logger.exception("LINE %s request error", log_label)
        return False
    finally:
        if own_client:
            await client.aclose()


async def reply_messages(reply_token: str, messages: list[dict[str, Any]]) -> bool:
    if not reply_token or not messages:
        return False
    return await _post_json(
        LINE_REPLY_URL,
        {"replyToken": reply_token, "messages": messages},
        log_label="reply",
    )


async def push_messages(user_id: str, messages: list[dict[str, Any]]) -> bool:
    if not user_id or not messages:
        return False
    return await _post_json(
        LINE_PUSH_URL,
        {"to": user_id, "messages": messages},
        log_label="push",
    )
