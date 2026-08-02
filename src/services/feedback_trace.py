"""
フィードバック非同期保存とトレースメタデータ（不具合調査用）。
ユーザー操作をブロックせず、失敗時もユーザーへ通知しない。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="feedback_async")


def shutdown_feedback_trace_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)


def build_feedback_trace(
    *,
    source: str,
    event: str,
    **extra: Any,
) -> dict[str, Any]:
    """調査用トレース辞書を組み立てる。"""
    trace: dict[str, Any] = {
        "source": source,
        "event": event,
        "recorded_at": datetime.now().isoformat(),
    }
    for key, value in extra.items():
        if value is not None:
            trace[key] = value
    return trace


def _project_log_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "log")


def _append_trace_jsonl_async(entry: dict[str, Any]) -> None:
    def _write() -> None:
        try:
            path = os.path.join(_project_log_dir(), "feedback_trace.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            logger.warning("Failed to write feedback trace log: %s", exc)

    threading.Thread(target=_write, name="feedback-trace-log", daemon=True).start()


def submit_feedback_async(
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
) -> None:
    """バックグラウンドでフィードバックを保存する（失敗はログのみ）。"""

    def _run() -> None:
        trace_entry = {
            "report_type": report_type,
            "session_id": session_id,
            "username": username,
            "metadata": metadata or {},
            "started_at": datetime.now().isoformat(),
        }
        try:
            from src.services.feedback_submit import FeedbackSubmitError, submit_feedback_record

            result = submit_feedback_record(
                report_type=report_type,
                session_id=session_id,
                username=username,
                user_message=user_message,
                ai_response=ai_response,
                security_score=security_score,
                feedback_text=feedback_text,
                is_google_form=is_google_form,
                negative_reason=negative_reason,
                metadata=metadata,
                dedupe=dedupe,
            )
            trace_entry["status"] = "saved"
            trace_entry["feedback_id"] = result.get("feedback_id")
            trace_entry["storage"] = result.get("storage", "db")
            logger.info(
                "feedback_async_saved type=%s id=%s session=%s source=%s event=%s",
                report_type,
                result.get("feedback_id"),
                session_id,
                (metadata or {}).get("source"),
                (metadata or {}).get("event"),
            )
        except FeedbackSubmitError as exc:
            trace_entry["status"] = "submit_error"
            trace_entry["error"] = str(exc)
            trace_entry["status_code"] = exc.status_code
            logger.warning(
                "feedback_async_submit_error type=%s session=%s: %s",
                report_type,
                session_id,
                exc,
            )
        except Exception as exc:
            trace_entry["status"] = "unexpected_error"
            trace_entry["error"] = str(exc)
            logger.exception(
                "feedback_async_unexpected_error type=%s session=%s",
                report_type,
                session_id,
            )
        finally:
            trace_entry["finished_at"] = datetime.now().isoformat()
            _append_trace_jsonl_async(trace_entry)

    _executor.submit(_run)
