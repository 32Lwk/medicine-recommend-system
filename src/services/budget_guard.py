"""
OpenAI API 予算ガード（月額 hard_stop / セッションコストアラート）
"""
from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple

from config.llm_config import OPENAI_MONTHLY_BUDGET_JPY, OPENAI_SESSION_COST_ALERT_JPY

logger = logging.getLogger(__name__)

_STATE_KEY = "OPENAI_MONTHLY_USAGE"
_SETTINGS_KEY = "LLM_ADMIN_SETTINGS"
DEFAULT_ALERT_EMAIL = "yuto.k051028@gmail.com"


def _db():
    from src.services.database import get_database
    return get_database()


def _db_ready(db) -> bool:
    return bool(db and db.is_available())


def _current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def get_monthly_usage() -> Dict[str, Any]:
    db = _db()
    default = {"month": _current_month(), "cost_jpy": 0.0, "hard_stopped": False}
    if not _db_ready(db):
        return default
    data = db.get_global_state(
        _STATE_KEY,
        default_value={"month": _current_month(), "cost_jpy": 0.0, "hard_stopped": False},
    )
    if data.get("month") != _current_month():
        data = {"month": _current_month(), "cost_jpy": 0.0, "hard_stopped": False}
        db.set_global_state(_STATE_KEY, data)
    return data


def add_monthly_cost(cost_jpy: float) -> Dict[str, Any]:
    if cost_jpy <= 0:
        return get_monthly_usage()
    db = _db()
    usage = get_monthly_usage()
    usage["cost_jpy"] = float(usage.get("cost_jpy", 0)) + float(cost_jpy)
    if usage["cost_jpy"] >= OPENAI_MONTHLY_BUDGET_JPY:
        usage["hard_stopped"] = True
        logger.warning(
            "OpenAI monthly budget exceeded: %.2f >= %s JPY",
            usage["cost_jpy"],
            OPENAI_MONTHLY_BUDGET_JPY,
        )
    if _db_ready(db):
        db.set_global_state(_STATE_KEY, usage)
    return usage


def is_llm_blocked() -> bool:
    return bool(get_monthly_usage().get("hard_stopped"))


def check_llm_allowed() -> Tuple[bool, Optional[str]]:
    if is_llm_blocked():
        msg = get_admin_message("budget_hard_stop")
        return False, msg or "monthly_budget_exceeded"
    return True, None


def get_admin_settings() -> Dict[str, Any]:
    db = _db()
    default = {"messages": {}, "alert_email": ""}
    if not _db_ready(db):
        return default
    return db.get_global_state(_SETTINGS_KEY, default_value=default) or default


def set_admin_settings(settings: Dict[str, Any]) -> bool:
    db = _db()
    if not _db_ready(db):
        return False
    return db.set_global_state(_SETTINGS_KEY, settings)


def get_admin_message(key: str) -> str:
    settings = get_admin_settings()
    return (settings.get("messages") or {}).get(key) or ""


def set_admin_message(key: str, text: str) -> bool:
    settings = get_admin_settings()
    messages = dict(settings.get("messages") or {})
    messages[key] = text
    settings["messages"] = messages
    return set_admin_settings(settings)


def get_alert_email() -> str:
    return (get_admin_settings().get("alert_email") or "").strip()


def set_alert_email(email: str) -> bool:
    settings = get_admin_settings()
    settings["alert_email"] = email.strip()
    return set_admin_settings(settings)


def ensure_llm_admin_defaults() -> None:
    """管理画面用デフォルト（アラートメール等）"""
    if get_alert_email() != DEFAULT_ALERT_EMAIL:
        set_alert_email(DEFAULT_ALERT_EMAIL)


def maybe_alert_session_cost(session_id: str, session_cost_jpy: float) -> None:
    if session_cost_jpy < OPENAI_SESSION_COST_ALERT_JPY:
        return
    email = get_alert_email()
    if not email:
        logger.info(
            "Session cost alert skipped (no alert_email): sid=%s cost=%.2f",
            session_id,
            session_cost_jpy,
        )
        return
    subject = f"[medicine-recommend] セッションAPIコストアラート ({session_cost_jpy:.2f}円)"
    body = (
        f"セッションID: {session_id}\n"
        f"推定コスト: {session_cost_jpy:.2f} 円\n"
        f"閾値: {OPENAI_SESSION_COST_ALERT_JPY} 円\n"
        f"時刻: {datetime.now().isoformat()}\n"
    )
    _send_email(email, subject, body)


def _send_email(to_addr: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", user or "noreply@localhost")
    if not host or not user:
        logger.warning("SMTP not configured; alert logged only: %s", subject)
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send alert email: %s", e)
        return False
