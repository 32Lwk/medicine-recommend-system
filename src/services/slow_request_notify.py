"""「時間がかかっている」通知 — ログ + SMTP"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from src.services.budget_guard import _send_email, get_alert_email

logger = logging.getLogger(__name__)


def notify_slow_request(
    session_id: Optional[str],
    *,
    client_ip: str = "",
    user_agent: str = "",
    last_user_message: str = "",
) -> None:
    msg_preview = (last_user_message or "")[:200]
    logger.warning(
        "slow_request sid=%s ip=%s ua=%s message=%s",
        session_id,
        client_ip,
        (user_agent or "")[:80],
        msg_preview,
    )
    email = get_alert_email()
    if not email:
        return
    subject = "[medicine-recommend] チャット応答が遅延しています"
    body = (
        f"セッションID: {session_id or '—'}\n"
        f"IP: {client_ip or '—'}\n"
        f"User-Agent: {(user_agent or '')[:120]}\n"
        f"直近メッセージ: {msg_preview}\n"
        f"時刻: {datetime.now().isoformat()}\n"
    )
    _send_email(email, subject, body)
