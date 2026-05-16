"""
通知メール送信の抽象化（SMTP 実装 / スタブ）
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailNotifier(Protocol):
    def send(self, to_addr: str, subject: str, body: str) -> str:
        """Returns: sent | failed | skipped_no_email | smtp_not_configured | skipped_disabled"""
        ...


class SmtpEmailNotifier:
    def send(self, to_addr: str, subject: str, body: str) -> str:
        if not to_addr:
            return "skipped_no_email"
        from src.services.budget_guard import _send_email

        if _send_email(to_addr, subject, body):
            return "sent"
        return "failed"


class StubEmailNotifier:
    def send(self, to_addr: str, subject: str, body: str) -> str:
        logger.info("email stub: to=%s subject=%s", to_addr, subject[:80])
        return "stub"


def get_email_notifier(*, force_stub: bool = False) -> EmailNotifier:
    import os

    if force_stub or os.getenv("EMERGENCY_EMAIL_FORCE_STUB", "").lower() in ("1", "true", "yes"):
        return StubEmailNotifier()
    return SmtpEmailNotifier()
