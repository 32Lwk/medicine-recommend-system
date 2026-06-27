"""LINE Messaging API Reply / Push クライアント。"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

import httpx

from config.line_config import get_line_channel_access_token

logger = logging.getLogger(__name__)

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_LOADING_START_URL = "https://api.line.me/v2/bot/chat/loading/start"
LINE_LOADING_SECONDS_MIN = 5
LINE_LOADING_SECONDS_MAX = 60

_http_client: httpx.AsyncClient | None = None
_thread_local = threading.local()


def set_http_client(client: httpx.AsyncClient | None) -> None:
    global _http_client
    _http_client = client


def acquire_thread_http_client() -> httpx.AsyncClient:
    """バックグラウンドスレッド用の再利用可能な httpx クライアント。"""
    client = getattr(_thread_local, "client", None)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=5),
        )
        _thread_local.client = client
    return client


def _headers() -> dict[str, str] | None:
    token = get_line_channel_access_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def resolve_http_client() -> httpx.AsyncClient:
    """lifespan クライアントがあればそれを、なければスレッドローカルを返す。"""
    client = _http_client
    if client is None or client.is_closed:
        client = acquire_thread_http_client()
    return client


def _mark_reply_token_unavailable(status_code: int, body: str) -> None:
    """Reply token 失効・使用済み時は Push フォールバックを抑止（二重配信防止）。"""
    if status_code != 400:
        return
    lower = (body or "").lower()
    if "reply token" not in lower and "replytoken" not in lower:
        return
    try:
        from src.handlers.line.line_progressive_delivery import get_line_delivery_context

        ctx = get_line_delivery_context()
        if ctx is not None:
            ctx.reply_token_unavailable = True
    except ImportError:
        pass


async def _post_json(url: str, payload: dict[str, Any], *, log_label: str) -> bool:
    hdrs = _headers()
    if not hdrs:
        logger.warning("LINE %s skipped: LINE_CHANNEL_ACCESS_TOKEN not configured", log_label)
        return False

    client = resolve_http_client()
    try:
        response = await client.post(url, headers=hdrs, json=payload)
        if response.status_code >= 400:
            body = (response.text or "")[:500]
            if log_label == "reply":
                _mark_reply_token_unavailable(response.status_code, body)
            logger.warning(
                "LINE %s failed status=%s body=%s",
                log_label,
                response.status_code,
                body,
            )
            return False
        logger.info("LINE %s ok", log_label)
        return True
    except Exception:
        logger.exception("LINE %s request error", log_label)
        return False


async def get_json(url: str, *, log_label: str = "get") -> dict[str, Any] | None:
    """LINE API GET（プロフィール取得など）。"""
    hdrs = _headers()
    if not hdrs:
        logger.warning("LINE %s skipped: LINE_CHANNEL_ACCESS_TOKEN not configured", log_label)
        return None
    client = resolve_http_client()
    try:
        response = await client.get(url, headers=hdrs)
        if response.status_code >= 400:
            logger.warning(
                "LINE %s failed status=%s body=%s",
                log_label,
                response.status_code,
                (response.text or "")[:500],
            )
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception:
        logger.exception("LINE %s request error", log_label)
        return None


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


def _normalize_loading_seconds(raw: int | None) -> int:
    """LINE loading API: 5〜60 秒、5 秒刻み。"""
    if raw is None:
        try:
            raw = int(os.getenv("LINE_LOADING_SECONDS", "60"))
        except (TypeError, ValueError):
            raw = 60
    clamped = max(LINE_LOADING_SECONDS_MIN, min(LINE_LOADING_SECONDS_MAX, raw))
    return 5 * round(clamped / 5)


async def start_loading_animation(user_id: str, *, loading_seconds: int | None = None) -> bool:
    """
    1:1 チャットで LINE 標準のローディング表示（…）を出す。
    公式アカウントから次のメッセージが届くと自動で消える。
    """
    if not user_id:
        return False
    seconds = _normalize_loading_seconds(loading_seconds)
    return await _post_json(
        LINE_LOADING_START_URL,
        {"chatId": user_id, "loadingSeconds": seconds},
        log_label="loading",
    )
