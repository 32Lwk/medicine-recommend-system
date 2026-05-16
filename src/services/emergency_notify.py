"""
緊急事案の手動キュー登録時メール通知（SMTP / 管理アラート先）
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from src.services.budget_guard import get_alert_email
from src.services.email_notifier import get_email_notifier
from src.utils.admin_snippet import truncate_user_text

logger = logging.getLogger(__name__)

_PRIORITY_SUBJECT = {
    "critical_crisis": "[CRITICAL-CRISIS]",
    "critical_medical": "[CRITICAL-MEDICAL]",
    "store_high": "[STORE-HIGH]",
    "store_low": "[STORE-LOW]",
}

_SUBTYPE_LABEL = {
    "crisis_language": "クライシス",
    "medical_self": "メディカル緊急",
    "store_incident": "店舗インシデント",
}


def is_emergency_email_enabled() -> bool:
    val = os.getenv("EMERGENCY_EMAIL_ENABLED", "true").strip().lower()
    return val in ("1", "true", "yes", "on")


def notify_emergency_detected(
    *,
    session_id: str,
    user_message: str,
    priority_tag: str,
    emergency_subtype: str,
    emergency_type: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> str:
    """
    緊急検出をアラートメールへ通知。
    Returns: sent | skipped_disabled | skipped_no_email | smtp_not_configured | failed
    """
    snippet = truncate_user_text(user_message, "list")
    logger.warning(
        "emergency_detected sid=%s priority=%s subtype=%s message=%s",
        session_id,
        priority_tag,
        emergency_subtype,
        snippet,
    )

    if not is_emergency_email_enabled():
        return "skipped_disabled"

    email = get_alert_email()
    if not email:
        return "skipped_no_email"

    pri = _PRIORITY_SUBJECT.get(priority_tag, "[EMERGENCY]")
    subtype_label = _SUBTYPE_LABEL.get(emergency_subtype, emergency_subtype)
    type_part = emergency_type or emergency_subtype or "unknown"
    subject = f"[medicine-recommend] {pri} 緊急事案 — {subtype_label}"
    detail = truncate_user_text(user_message, "detail")
    body = (
        f"優先度: {priority_tag}\n"
        f"種別: {subtype_label} ({type_part})\n"
        f"セッションID: {session_id}\n"
        f"trace_id: {trace_id or '—'}\n"
        f"時刻: {datetime.now().isoformat()}\n"
        f"\n--- ユーザー入力（最大800文字）---\n"
        f"{detail}\n"
        f"\n管理画面の手動返信キューで確認してください。\n"
    )
    return get_email_notifier().send(email, subject, body)


def build_notification_status(email_result: str) -> Dict[str, str]:
    return {"email": email_result, "admin": "pending"}
