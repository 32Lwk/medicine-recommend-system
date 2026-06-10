"""LINE userId とアプリセッション（sid）の紐付け。"""
from __future__ import annotations

import logging
from typing import Any

from src.services.session_manager import get_session_from_db, persist_session_from_chat_state
from src.utils.request_safe_session import RequestSafeSession

logger = logging.getLogger(__name__)

LINE_SID_PREFIX = "line:"
LINE_CLIENT_IP = "line-webhook"
DEFAULT_USER_ATTRS: dict[str, Any] = {
    "age": None,
    "gender": None,
    "pregnant": None,
    "breastfeeding": None,
    "current_medications": [],
    "allergies": [],
    "medical_history": [],
    "symptom_duration_days": None,
    "other_info": None,
}


def line_sid(user_id: str) -> str:
    return f"{LINE_SID_PREFIX}{user_id}"


def prime_line_session(user_id: str) -> RequestSafeSession:
    sid = line_sid(user_id)
    session = RequestSafeSession()
    session.setdefault("messages", [])
    session.setdefault("user_attributes", dict(DEFAULT_USER_ATTRS))
    session["_id"] = sid
    if "username" not in session:
        session["username"] = f"LINEユーザー{user_id[-6:]}"

    session_data = get_session_from_db(sid)
    if session_data:
        session["messages"] = (session_data.get("messages") or []).copy()
        db_attrs = session_data.get("user_attributes") or {}
        if db_attrs:
            current = session.get("user_attributes", {}) or {}
            session["user_attributes"] = {**current, **db_attrs}
        if session_data.get("username"):
            session["username"] = session_data["username"]
        for flag in (
            "detected_language",
            "medical_emergency_otc_locked",
            "crisis_detected",
            "emergency_detected",
        ):
            if flag in session_data:
                session[flag] = session_data[flag]
    return session


def get_latest_bot_message_from_session(session: Any) -> dict | None:
    """インメモリセッションから最新の bot メッセージを取得。"""
    messages = session.get("messages") if hasattr(session, "get") else []
    if not messages:
        return None
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("type") == "bot":
            return msg
    return None


def get_latest_bot_message(sid: str) -> dict | None:
    """DB から最新の bot メッセージを取得（末尾から最初の type=bot）。"""
    session_data = get_session_from_db(sid)
    if not session_data:
        return None
    messages = session_data.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("type") == "bot":
            return msg
    return None


def resolve_latest_bot_message(session: Any, sid: str) -> dict | None:
    """パイプライン直後はインメモリを優先し、なければ DB を参照する。"""
    bot = get_latest_bot_message_from_session(session)
    if bot:
        return bot
    return get_latest_bot_message(sid)


def persist_line_session(sid: str, session: RequestSafeSession) -> None:
    persist_session_from_chat_state(sid, session, request=None)
