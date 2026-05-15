"""
セッション同期・チャット終了・眠気/不眠キーワード triage 上書き
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.services.session_manager import (
    append_user_message,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

CHAT_END_WORDS = frozenset(["終了", "end", "おわり", "終わり", "quit", "exit"])


def handle_chat_end_if_requested(
    session: Any,
    sid: Optional[str],
    sanitized_message: str,
) -> Optional[ResponseTuple]:
    if sanitized_message not in CHAT_END_WORDS:
        return None

    logger.info("🔚 CHAT ENDED by user: %s", session.get("username", "unknown"))
    if hasattr(session, "modified"):
        session.modified = True
    session.setdefault("messages", []).append({
        "type": "bot",
        "content": (
            "チャットを終了しました。不明点がございましたら、"
            "お気軽にお近くの登録販売者にご相談ください。"
        ),
        "diagnosis": None,
        "chat_ended": True,
    })
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = session["messages"].copy()
            session_data["last_activity"] = datetime.now()
            session_data["session_active"] = False
            save_session_to_db(sid, session_data)
    message_count = len(session["messages"])
    logger.info("✅ POST処理完了（チャット終了） - JSON返却: %s messages", message_count)
    return ({"status": "ok", "message_count": message_count}, 200)


def append_user_message_if_needed(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    original_user_message: str,
) -> None:
    """セッションと DB にユーザーメッセージを追加（重複防止）"""
    if was_last_user_message(session, original_user_message):
        return
    user_msg = append_user_message(session, original_user_message)
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if session_data:
        session_data.setdefault("messages", [])
        if not was_last_user_message(session_data, original_user_message):
            session_data["messages"].append(user_msg)
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)
    else:
        save_session_to_db(
            sid,
            {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session.get("messages", []),
                "session_active": True,
                "last_activity": datetime.now(),
                "client_ip": client_info.client_ip,
                "user_agent": client_info.user_agent,
                "user_attributes": session.get("user_attributes", {}),
            },
        )


def sync_messages_to_db_for_admin(
    session: Any,
    sid: Optional[str],
    client_info: Any,
) -> None:
    """管理画面表示用に DB へユーザーメッセージを即時反映"""
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if not session_data:
        save_session_to_db(
            sid,
            {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session.get("messages", []).copy(),
                "last_activity": datetime.now(),
                "client_ip": client_info.client_ip,
                "user_agent": client_info.user_agent,
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
            },
        )
        return

    if session.get("is_medicine_consultation", False):
        logger.info("📝 医薬品相談回答処理中のため、DB即時反映を完全にスキップ")
        return

    existing_messages = session_data.get("messages", [])
    new_user_messages = [m for m in session.get("messages", []) if m.get("type") == "user"]
    for new_msg in new_user_messages:
        if not any(
            ex.get("type") == "user"
            and ex.get("content") == new_msg.get("content")
            and ex.get("uuid") == new_msg.get("uuid")
            for ex in existing_messages
        ):
            existing_messages.append(new_msg)
    session_data["messages"] = existing_messages
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)


def apply_emotional_keyword_routing(
    session: Any,
    triage_result: Optional[Dict[str, Any]],
    sanitized_message: str,
    *,
    phase: str,
) -> Optional[str]:
    """
    眠気/不眠キーワードで triage を Emotional に上書き。
    phase: "sleepiness" | "insomnia"
    上書き後の category 文字列、または None。
    """
    from src.handlers.chat.chat_emotional_route import (
        apply_emotional_keyword_triage_overrides,
        detect_insomnia_keyword,
        detect_sleepiness_keyword,
    )

    if phase == "sleepiness":
        has_sleepiness = detect_sleepiness_keyword(sanitized_message)
        session["has_sleepiness_keyword"] = has_sleepiness
        if has_sleepiness and not session.get("sleepiness_medicine_recommendation"):
            logger.info(
                "🔄 眠気関連キーワードを検出: カウンセリングフローにリダイレクト (category=%s)",
                triage_result.get("category", "N/A") if triage_result else "N/A",
            )
            return apply_emotional_keyword_triage_overrides(
                triage_result,
                sanitized_message,
                has_sleepiness_keyword=True,
                has_insomnia_keyword=False,
                session=session,
            )
        return None

    has_sleepiness = session.get("has_sleepiness_keyword", False)
    skip_insomnia = has_sleepiness
    has_insomnia = detect_insomnia_keyword(sanitized_message)
    session["has_insomnia_keyword"] = has_insomnia

    if has_insomnia and not session.get("insomnia_medicine_recommendation") and not skip_insomnia:
        logger.info(
            "🔄 不眠関連キーワードを検出: カウンセリングフローにリダイレクト (category=%s)",
            triage_result.get("category", "N/A") if triage_result else "N/A",
        )
        return apply_emotional_keyword_triage_overrides(
            triage_result,
            sanitized_message,
            has_sleepiness_keyword=has_sleepiness,
            has_insomnia_keyword=True,
            skip_insomnia_check=skip_insomnia,
            session=session,
        )
    return None
