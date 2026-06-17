"""
開発環境向けフィードバック保存（DATABASE_URL 未設定時のフォールバック）。

メモリに保持し、log/feedback_dev.jsonl へ非同期追記する。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_dev_feedback: List[Dict[str, Any]] = []
_counter = 0


def _project_log_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "log")


def save_feedback_dev(
    *,
    report_type: str,
    session_id: str,
    username: str,
    user_message: str,
    ai_response: str,
    security_score: Optional[float] = None,
    feedback_text: Optional[str] = None,
    is_google_form: bool = False,
    negative_reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """DB なし開発環境へフィードバックを保存し、擬似 ID を返す。"""
    global _counter
    entry: Dict[str, Any] = {
        "report_type": report_type,
        "session_id": session_id or "",
        "username": username or "Unknown",
        "user_message": user_message or "",
        "ai_response": ai_response or "",
        "security_score": security_score,
        "feedback_text": feedback_text or "",
        "is_google_form": bool(is_google_form),
        "negative_reason": negative_reason,
        "metadata": metadata or {},
        "resolved": False,
        "created_at": datetime.now().isoformat(),
        "storage": "dev_fallback",
    }
    with _lock:
        _counter += 1
        entry["id"] = _counter
        _dev_feedback.append(entry)
        feedback_id = _counter

    _append_jsonl_async(entry)
    logger.info(
        "✅ Feedback saved (dev fallback) id=%s type=%s session=%s",
        feedback_id,
        report_type,
        session_id,
    )
    return feedback_id


def list_feedback_dev(*, limit: int = 100, unresolved_only: bool = False) -> List[Dict[str, Any]]:
    with _lock:
        rows = list(_dev_feedback)
    if unresolved_only:
        rows = [r for r in rows if not r.get("resolved")]
    return rows[-limit:][::-1]


def resolve_feedback_dev(feedback_id: int) -> bool:
    with _lock:
        for row in _dev_feedback:
            if row.get("id") == feedback_id:
                row["resolved"] = True
                return True
    return False


def delete_feedback_dev(feedback_id: int) -> bool:
    global _dev_feedback
    with _lock:
        before = len(_dev_feedback)
        _dev_feedback = [r for r in _dev_feedback if r.get("id") != feedback_id]
        return len(_dev_feedback) < before


def _append_jsonl_async(entry: Dict[str, Any]) -> None:
    def _write() -> None:
        try:
            path = os.path.join(_project_log_dir(), "feedback_dev.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Failed to write dev feedback log: %s", exc)

    threading.Thread(target=_write, name="feedback-dev-log", daemon=True).start()
