"""
フィードバック保存（Web API / LINE postback 共通）。
"""
from __future__ import annotations

import time
from typing import Any

from config.app_config import is_development_runtime
from src.services.database import get_database
from src.services.session_manager import get_session_from_db, save_session_to_db


class FeedbackSubmitError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _apply_dedupe(session_id: str, payload: dict[str, Any]) -> None:
    if not session_id:
        return
    session_data = get_session_from_db(session_id) or {}
    current_time = time.time()
    dedupe_key = "|".join(
        [
            str(payload.get("report_type", "")),
            str(payload.get("user_message", ""))[:500],
            str(payload.get("ai_response", ""))[:500],
        ]
    )
    recent = session_data.get("feedback_recent_keys") or {}
    if not isinstance(recent, dict):
        recent = {}
    last_at = float(recent.get(dedupe_key, 0) or 0)
    if current_time - last_at < 60:
        raise FeedbackSubmitError(
            "Already submitted for this message. Please wait 60 seconds.",
            status_code=429,
        )
    recent[dedupe_key] = current_time
    session_data["feedback_recent_keys"] = {
        k: v for k, v in recent.items() if current_time - float(v) < 3600
    }
    save_session_to_db(session_id, session_data)


def submit_feedback_record(
    *,
    report_type: str,
    session_id: str,
    username: str,
    user_message: str,
    ai_response: str,
    security_score: float | None = None,
    feedback_text: str = "",
    is_google_form: bool = False,
    negative_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    dedupe: bool = True,
) -> dict[str, Any]:
    """DB または開発フォールバックへフィードバックを保存する。"""
    if len(feedback_text) > 1000:
        raise FeedbackSubmitError("Feedback text too long (max 1000 characters)")

    payload = dict(
        report_type=report_type,
        session_id=session_id or "",
        username=username or "Unknown",
        user_message=user_message or "",
        ai_response=ai_response or "",
        security_score=security_score,
        feedback_text=feedback_text or "",
        is_google_form=bool(is_google_form),
        negative_reason=negative_reason,
        metadata=metadata,
    )

    if dedupe:
        _apply_dedupe(session_id, payload)

    db = get_database()
    if db and (db.connection or db.connection_pool):
        feedback_id = db.insert_feedback(**payload)
        if not feedback_id:
            raise FeedbackSubmitError("Failed to save feedback", status_code=500)
        return {"status": "success", "feedback_id": feedback_id}

    if is_development_runtime():
        from src.services.feedback_store import save_feedback_dev

        feedback_id = save_feedback_dev(**payload)
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "storage": "dev_fallback",
        }

    raise FeedbackSubmitError("Database not available", status_code=500)
