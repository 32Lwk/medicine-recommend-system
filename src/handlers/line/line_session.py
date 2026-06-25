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
    return bool(sid and str(sid).lower().startswith(LINE_SID_PREFIX))


def normalize_line_session_id(sid: str | None) -> str | None:
    """`line:` / `LINE:` 混在を小文字 `line:` に統一。"""
    if not sid:
        return None
    raw = str(sid).strip()
    if raw.lower().startswith(LINE_SID_PREFIX):
        return LINE_SID_PREFIX + raw[len(LINE_SID_PREFIX) :]
    return raw


def user_id_from_line_sid(sid: str | None) -> str | None:
    """`line:{userId}` 形式のセッション ID から LINE userId を取り出す。"""
    normalized = normalize_line_session_id(sid)
    if not normalized or not is_line_session_id(normalized):
        return None
    user_id = normalized[len(LINE_SID_PREFIX) :].strip()
    return user_id or None


def resolve_session_line_context(
    sess_id: str | None,
    info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    管理画面用: LINE 本体 / LINE→Web 引き継ぎ / 純 Web を解決する。

    LINE Webhook の会話は常に `line:{userId}` に保存される。
    数値 session_id は Web チャット（ブラウザ）または引き継ぎ先。
    """
    sid = str(sess_id or "")
    data = info if isinstance(info, dict) else {}
    native = is_line_session_id(sid)
    handoff = normalize_line_session_id(str(data.get("handoff_from_line") or ""))
    handoff_valid = bool(handoff and is_line_session_id(handoff))
    try:
        from src.services.line_user_memory import resolve_memory_owner_sid

        memory_owner = resolve_memory_owner_sid(sid, data)
    except ImportError:
        memory_owner = handoff if handoff_valid else (sid if native else None)
    line_related = native or handoff_valid
    return {
        "is_line_session": native,
        "is_line_handoff": handoff_valid and not native,
        "is_line_related": line_related,
        "handoff_from_line": handoff if handoff_valid else None,
        "line_memory_owner_sid": memory_owner if line_related else None,
    }


def trim_line_session_messages(
    session: Any,
    *,
    max_messages: int = LINE_SESSION_MAX_MESSAGES,
    sid: str | None = None,
    session_data: dict | None = None,
) -> None:
    """LINE セッションの会話履歴を上限件数に抑え、プロンプト肥大化を防ぐ（管理用アーカイブは別途保持）。"""
    messages = session.get("messages") if hasattr(session, "get") else None
    if not isinstance(messages, list) or len(messages) <= max_messages:
        return
    before = len(messages)
    dropped = before - max_messages
    session["messages"] = messages[-max_messages:]
    from src.services.session_lifecycle import append_lifecycle_event

    log_target = session_data if isinstance(session_data, dict) else session
    append_lifecycle_event(
        log_target,
        "message_trim",
        source="line_session.trim_line_session_messages",
        detail=f"LLM用 messages を最新 {max_messages} 件に制限（{dropped} 件を切り捨て。管理画面は message_archive に保持）",
        messages_before=before,
        messages_after=max_messages,
        extra={"dropped_count": dropped, "max_messages": max_messages},
    )
    if sid and isinstance(session_data, dict):
        from src.services.session_manager import save_session_to_db

        save_session_to_db(sid, session_data)


def clear_line_session_state(session: Any, *, sid: str | None = None, session_data: dict | None = None) -> None:
    """チャット終了時に LINE セッションの会話・一時フラグをリセットする。"""
    from src.services.session_lifecycle import merge_messages_into_archive

    msgs = list(session.get("messages") or []) if hasattr(session, "get") else []
    messages_before = len(msgs)
    log_target = session_data if isinstance(session_data, dict) else session
    if msgs and log_target is not None:
        merge_messages_into_archive(log_target, msgs)
    session["messages"] = []
    session.pop("counseling_mode", None)
    session.pop("last_triage_result", None)
    session.pop("_last_triage_result", None)
    session["concierge_state"] = {"off_topic_turns": 0, "last_intent": None}
    line_sid = sid if sid and str(sid).startswith("line:") else None
    if line_sid:
        from src.services.line_memory_jobs import schedule_episode_summary, schedule_profile_persist
        from src.services.line_user_memory import (
            get_current_episode_id,
            load_line_memory,
            profile_to_user_attributes,
            reset_current_episode_id,
        )

        attrs = dict(session.get("user_attributes") or {}) if hasattr(session, "get") else {}
        schedule_profile_persist(line_sid, attrs)
        episode_id = get_current_episode_id(line_sid)
        schedule_episode_summary(line_sid, msgs, trigger="chat_end", episode_id=episode_id)
        reset_current_episode_id(line_sid)
        profile, _ = load_line_memory(line_sid)
        if hasattr(session, "__setitem__"):
            session["user_attributes"] = profile_to_user_attributes(profile)
    else:
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

    from src.services.session_lifecycle import append_lifecycle_event

    log_target = session_data if isinstance(session_data, dict) else session
    append_lifecycle_event(
        log_target,
        "history_cleared",
        source="line_session.clear_line_session_state",
        detail="ユーザーがチャット終了。messages は空にしたが message_archive は保持",
        messages_before=messages_before,
        messages_after=0,
    )
    if sid and isinstance(session_data, dict):
        from src.services.session_manager import save_session_to_db

        save_session_to_db(sid, session_data)


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
        if session_data.get("line_profile"):
            session["line_profile"] = session_data["line_profile"]
        for flag in (
            "detected_language",
            "language",
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
    owner_sid = line_sid(user_id)
    from src.services.line_user_memory import apply_profile_to_session

    apply_profile_to_session(session, owner_sid, session_data=session_data)
    if session_data:
        from src.services.session_lifecycle import merge_messages_into_archive

        merge_messages_into_archive(session_data, session.get("messages") or [])
        if session_data.get("lifecycle_log") and not session.get("lifecycle_log"):
            session["lifecycle_log"] = session_data.get("lifecycle_log")
        trim_line_session_messages(session, sid=sid, session_data=session_data)
        from src.services.session_manager import save_session_to_db

        save_session_to_db(sid, session_data)
    else:
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


def count_bot_messages_in_session(session: Any) -> int:
    """インメモリセッション内の bot メッセージ数。"""
    messages = session.get("messages") if hasattr(session, "get") else []
    return sum(1 for m in messages if isinstance(m, dict) and m.get("type") == "bot")


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
    from src.services.pipeline_perf import mark_pipeline_step
    from src.services.session_lifecycle import merge_messages_into_archive
    from src.services.session_manager import get_session_from_memory, touch_session_in_memory

    mark_pipeline_step("session_db_write")
    session_data = get_session_from_memory(sid) or {"session_id": sid, "messages": []}
    msgs = session.get("messages") if hasattr(session, "get") else []
    if msgs:
        merge_messages_into_archive(session_data, msgs)
    if session.get("line_profile"):
        session_data["line_profile"] = session["line_profile"]
    if session.get("lifecycle_log"):
        session_data["lifecycle_log"] = session.get("lifecycle_log")
    trim_line_session_messages(session, sid=sid, session_data=session_data)
    touch_session_in_memory(sid, session_data)
    persist_session_from_chat_state(sid, session, request=None, force_persist=True, session_data=session_data)
