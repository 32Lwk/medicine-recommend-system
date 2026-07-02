"""「時間がかかっている」通知 — ログ + SMTP + 不具合報告一覧への非同期保存"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

from src.services.budget_guard import _send_email, get_alert_email
from src.services.feedback_trace import build_feedback_trace, submit_feedback_async

logger = logging.getLogger(__name__)


def _summarize_processing_status(status: Optional[dict[str, Any]]) -> str:
    if not isinstance(status, dict) or not status.get("active"):
        return "（処理中・応答待ち）"
    step = status.get("current_step") or status.get("step_id") or ""
    label = status.get("label") or status.get("current_label") or ""
    percent = status.get("percent")
    parts = ["（処理中・応答待ち）"]
    if step:
        parts.append(f"step={step}")
    if label:
        parts.append(f"label={label}")
    if percent is not None:
        parts.append(f"progress={percent}%")
    return " / ".join(parts)


def _build_session_investigation_snapshot(
    session_data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(session_data, dict):
        return {}
    msgs = session_data.get("messages")
    snap: dict[str, Any] = {}
    if isinstance(msgs, list):
        snap["message_count"] = len(msgs)
        if msgs:
            last = msgs[-1]
            if isinstance(last, dict):
                snap["last_message_type"] = last.get("type")
                diagnosis = last.get("diagnosis")
                if isinstance(diagnosis, dict):
                    for key in ("render", "flow_id", "medicine_type"):
                        if diagnosis.get(key):
                            snap[f"last_bot_{key}"] = diagnosis.get(key)
    for key in ("username", "channel", "line_user_id"):
        value = session_data.get(key)
        if value:
            snap[key] = value
    return snap


def notify_slow_request(
    session_id: Optional[str],
    *,
    client_ip: str = "",
    user_agent: str = "",
    last_user_message: str = "",
    username: str = "",
    processing_status: Optional[dict[str, Any]] = None,
    client_context: Optional[dict[str, Any]] = None,
    session_investigation: Optional[dict[str, Any]] = None,
    pipeline_perf_snapshot: Optional[dict[str, Any]] = None,
) -> None:
    msg_preview = (last_user_message or "")[:200]
    logger.warning(
        "slow_request sid=%s ip=%s ua=%s message=%s",
        session_id,
        client_ip,
        (user_agent or "")[:80],
        msg_preview,
    )

    trace = build_feedback_trace(
        source="web",
        event="slow_request_notify",
        session_id=session_id,
        client_ip=client_ip,
        user_agent=(user_agent or "")[:200],
        last_user_message=msg_preview,
        processing_status=processing_status,
        client_context=client_context or {},
        session_investigation=session_investigation or {},
        pipeline_perf_snapshot=pipeline_perf_snapshot,
        server_time=datetime.now().isoformat(),
        pid=os.getpid(),
    )

    submit_feedback_async(
        report_type="slow_request",
        session_id=session_id or "",
        username=username or "Unknown",
        user_message=last_user_message or "",
        ai_response=_summarize_processing_status(processing_status),
        feedback_text="ユーザーが処理遅延を運営に通知しました",
        metadata=trace,
        dedupe=True,
    )

    email = get_alert_email()
    if not email:
        return
    subject = "[medicine-recommend] チャット応答が遅延しています"
    body = (
        f"セッションID: {session_id or '—'}\n"
        f"ユーザー: {username or '—'}\n"
        f"IP: {client_ip or '—'}\n"
        f"User-Agent: {(user_agent or '')[:120]}\n"
        f"直近メッセージ: {msg_preview}\n"
        f"処理状況: {_summarize_processing_status(processing_status)}\n"
        f"時刻: {datetime.now().isoformat()}\n"
    )
    _send_email(email, subject, body)
