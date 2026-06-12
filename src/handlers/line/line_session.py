"""LINE userId とアプリセッション（sid）の紐付け。"""
from __future__ import annotations

import logging
from typing import Any

from src.services.session_manager import persist_session_from_chat_state, get_session_from_memory
from src.utils.request_safe_session import RequestSafeSession

logger = logging.getLogger(__name__)

LINE_SID_PREFIX = "line:"
LINE_CLIENT_IP = "line-webhook"
LINE_SESSION_MAX_MESSAGES = 24
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


def is_line_session_id(sid: str | None) -> bool:
    return bool(sid and str(sid).startswith(LINE_SID_PREFIX))


def trim_line_session_messages(session: Any, *, max_messages: int = LINE_SESSION_MAX_MESSAGES) -> None:
    """LINE セッションの会話履歴を上限件数に抑え、プロンプト肥大化を防ぐ。"""
    messages = session.get("messages") if hasattr(session, "get") else None
    if not isinstance(messages, list) or len(messages) <= max_messages:
        return
    session["messages"] = messages[-max_messages:]


def clear_line_session_state(session: Any) -> None:
    """チャット終了時に LINE セッションの会話・一時フラグをリセットする。"""
    session["messages"] = []
    session.pop("counseling_mode", None)
    session.pop("last_triage_result", None)
    session.pop("_last_triage_result", None)
    session["concierge_state"] = {"off_topic_turns": 0, "last_intent": None}
    session["user_attributes"] = dict(DEFAULT_USER_ATTRS)
    for flag in (
        "medical_emergency_otc_locked",
        "crisis_detected",
        "emergency_detected",
        "store_incident_emergency",
        "has_sleepiness_keyword",
        "has_insomnia_keyword",
    ):
        session.pop(flag, None)


def prime_line_session(user_id: str) -> RequestSafeSession:
    sid = line_sid(user_id)
    session = RequestSafeSession()
    session.setdefault("messages", [])
    session.setdefault("user_attributes", dict(DEFAULT_USER_ATTRS))
    session["_id"] = sid
    if "username" not in session:
        session["username"] = f"LINEユーザー{user_id[-6:]}"

    # LINE 応答経路では DB 読込を避け、同一インスタンスのメモリのみ復元する。
    # （DB 接続不良時の getconn/再接続待ちで loading 後に数十秒ブロックするのを防ぐ）
    from src.services.session_manager import get_ai_auto_reply_in_memory, get_session_from_memory

    session_data = get_session_from_memory(sid)
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
            "concierge_state",
            "counseling_mode",
            "last_triage_result",
            "_last_triage_result",
        ):
            if flag in session_data:
                session[flag] = session_data[flag]
        if session_data.get("ai_auto_reply") is not None:
            session["ai_auto_reply"] = session_data["ai_auto_reply"]
    session.setdefault("ai_auto_reply", get_ai_auto_reply_in_memory())
    trim_line_session_messages(session)
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
    """メモリまたは DB から最新の bot メッセージを取得。"""
    session_data = get_session_from_memory(sid)
    if not session_data:
        from src.services.session_manager import get_session_from_db

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
    trim_line_session_messages(session)
    persist_session_from_chat_state(sid, session, request=None, force_persist=True)
