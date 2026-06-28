"""
パイプライン終端ガード — 当該ターンで bot 応答が無い場合に redirect を補完する。

Web / LINE 共通（サーバーサイド session.messages を参照）。
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.handlers.line.line_session import (
    count_bot_messages_in_session,
    get_latest_bot_message_from_session,
    resolve_latest_bot_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def append_redirect_bot_response(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    recommendation_client: Optional[OpenAI] = None,
) -> dict:
    """Concierge redirect テンプレートで bot メッセージを追記する。"""
    from src.agents.concierge_agent import build_concierge_payload
    from src.core.medicine_logic import client as default_client
    from src.handlers.chat.chat_concierge_route import (
        _append_bot_message,
        _mark_session_modified,
        _sync_session_db,
    )

    client = recommendation_client or default_client
    try:
        from src.dialogue.history import resolve_concierge_history_with_fallback

        history = resolve_concierge_history_with_fallback(session, sid)
    except Exception:
        history = []
    payload = build_concierge_payload("redirect", "", client, session_id=sid, history=history)
    bot = _append_bot_message(session, payload, sid)
    _mark_session_modified(session)
    if sid and client_info is not None:
        _sync_session_db(session, client_info, sid)
    logger.warning("Pipeline end guard: appended redirect bot sid=%s", sid)
    return bot


def _user_input_for_latest_bot(session: Any) -> str:
    """直近 bot の直前 user メッセージを返す。"""
    messages = session.get("messages") if hasattr(session, "get") else []
    if not messages:
        return ""
    last_bot_idx: int | None = None
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, dict) and msg.get("type") == "bot":
            last_bot_idx = idx
            break
    if last_bot_idx is None:
        return ""
    for idx in range(last_bot_idx - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, dict) and msg.get("type") == "user":
            content = msg.get("content")
            return str(content) if content is not None else ""
    return ""


def _schedule_turn_detail_log(
    session: Any,
    sid: Optional[str],
    *,
    user_message: Optional[str] = None,
) -> None:
    """新規 bot 応答があれば counseling_detail を非同期で記録（Web/LINE 共通）。"""
    effective_sid = sid or (
        str(session.get("session_id") or session.get("_id") or "")
        if isinstance(session, dict)
        else ""
    )
    bot_msg = resolve_latest_bot_message(session, effective_sid or None) or get_latest_bot_message_from_session(session)
    if not bot_msg:
        return
    user_input = (user_message or _user_input_for_latest_bot(session) or "").strip()
    if not user_input:
        return
    try:
        from src.services.counseling.counseling_logger import maybe_log_turn_counseling_detail

        maybe_log_turn_counseling_detail(session, effective_sid or None, user_input, bot_msg)
    except Exception as exc:
        logger.debug("turn detail log skipped: %s", exc)


def finalize_pipeline_response(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    bot_count_before: int,
    response: ResponseTuple,
    *,
    recommendation_client: Optional[OpenAI] = None,
    user_message: Optional[str] = None,
) -> ResponseTuple:
    """応答返却直前に bot 追記有無を確認する。無応答時は fail-loud（redirect 補完しない）。"""
    if count_bot_messages_in_session(session) > bot_count_before:
        if hasattr(session, "__setitem__"):
            session.pop("_pipeline_end_guard", None)
        _schedule_turn_detail_log(session, sid, user_message=user_message)
        return response

    logger.error(
        "Pipeline end guard: response_missing sid=%s user_input=%r",
        sid,
        (user_message or _user_input_for_latest_bot(session))[:200],
    )
    if hasattr(session, "__setitem__"):
        session["_pipeline_end_guard"] = "missing"
    _schedule_turn_detail_log(session, sid, user_message=user_message)
    body, status = response
    new_body = dict(body) if isinstance(body, dict) else {"status": "ok"}
    new_body["message_count"] = len(session.get("messages", []))
    new_body["pipeline_end_guard"] = "missing"
    return new_body, status
