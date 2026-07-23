"""
パイプライン終端ガード — 当該ターンで bot 応答が無い場合に redirect を補完する。

Web / LINE 共通（サーバーサイド session.messages を参照）。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.handlers.line.line_session import (
    count_bot_messages_in_session,
    get_latest_bot_message_from_session,
    resolve_latest_bot_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_PIPELINE_TURN_BOT_APPENDED_KEY = "_pipeline_turn_bot_appended"


def mark_pipeline_turn_bot_appended(session: Any) -> None:
    """Web の Cookie  slimming 等で messages を消す前に、当該ターンで bot 追記済みと記録。"""
    if hasattr(session, "__setitem__"):
        session[_PIPELINE_TURN_BOT_APPENDED_KEY] = True


def _turn_produced_bot_reply(session: Any, bot_count_before: int) -> bool:
    if session.get(_PIPELINE_TURN_BOT_APPENDED_KEY):
        return True
    return count_bot_messages_in_session(session) > bot_count_before


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


def append_system_error_bot_message(session: Any, sid: Optional[str]) -> dict[str, Any]:
    """想定外の無応答回復用 — system_error Sage カード bot。"""
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_system_error_status

    sage_diag = build_system_error_status().to_client_dict()
    legacy = str(sage_diag.get("message") or sage_diag.get("title") or "")
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy,
        uuid=str(uuid.uuid4()),
    )


def append_system_error_notice(session: Any, sid: Optional[str]) -> bool:
    """パイプライン無応答時に system_error カードを1件追加する。"""
    from src.services.session_manager import get_session_from_db, save_session_to_db

    bot = append_system_error_bot_message(session, sid)
    session.setdefault("messages", []).append(bot)
    if hasattr(session, "modified"):
        session.modified = True
    if sid:
        session_data = get_session_from_db(sid) or {}
        session_data["messages"] = session.get("messages", []).copy()
        session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)
    logger.warning("System error card appended by pipeline end guard sid=%s", sid)
    return True


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
    if _turn_produced_bot_reply(session, bot_count_before):
        if hasattr(session, "pop"):
            session.pop(_PIPELINE_TURN_BOT_APPENDED_KEY, None)
            session.pop("_pipeline_end_guard", None)
        _schedule_turn_detail_log(session, sid, user_message=user_message)
        return response

    try:
        from src.services.llm_unavailability import is_llm_infrastructure_degraded

        if is_llm_infrastructure_degraded(session):
            if hasattr(session, "__setitem__"):
                session.pop("_pipeline_end_guard", None)
            _schedule_turn_detail_log(session, sid, user_message=user_message)
            body, status = response
            new_body = dict(body) if isinstance(body, dict) else {"status": "ok"}
            new_body["message_count"] = len(session.get("messages", []))
            return new_body, status
    except Exception:
        pass

    logger.error(
        "Pipeline end guard: response_missing sid=%s user_input=%r",
        sid,
        (user_message or _user_input_for_latest_bot(session))[:200],
    )
    append_system_error_notice(session, sid)
    if hasattr(session, "__setitem__"):
        session["_pipeline_end_guard"] = "recovered"
    _schedule_turn_detail_log(session, sid, user_message=user_message)
    body, status = response
    new_body = dict(body) if isinstance(body, dict) else {"status": "ok"}
    new_body["message_count"] = len(session.get("messages", []))
    new_body["pipeline_end_guard"] = "recovered"
    return new_body, status
