"""
セッション同期・チャット終了・眠気/不眠キーワード検出（LLM トリアージは上書きしない）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from src.utils.jst_datetime import now_jst_iso

from src.services.session_manager import (
    append_user_message,
    ensure_session_persisted,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
    should_skip_append_user_message,
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
    farewell = (
        "チャットを終了しました。不明点がございましたら、"
        "お気軽にお近くの登録販売者にご相談ください。"
    )
    if sid and str(sid).startswith("line:"):
        from src.handlers.line.line_session import clear_line_session_state

        session_data_for_clear = get_session_from_db(sid) or {"session_id": sid}
        clear_line_session_state(session, sid=sid, session_data=session_data_for_clear)
        session.setdefault("messages", []).append({
            "type": "bot",
            "content": farewell,
            "diagnosis": None,
            "chat_ended": True,
        })
    else:
        session.setdefault("messages", []).append({
            "type": "bot",
            "content": farewell,
            "diagnosis": None,
            "chat_ended": True,
        })
    if sid:
        session_data = get_session_from_db(sid) or {"session_id": sid}
        if str(sid).startswith("line:"):
            from src.handlers.line.line_session import clear_line_session_state
            from src.handlers.line.line_feedback import clear_line_feedback_pending

            clear_line_session_state(session_data, sid=sid, session_data=session_data)
            session_data["messages"] = session["messages"].copy()
            clear_line_feedback_pending(sid)
        else:
            session_data["messages"] = session["messages"].copy()
        session_data["last_activity"] = now_jst_iso()
        session_data["session_active"] = False
        from src.services.session_lifecycle import append_lifecycle_event

        append_lifecycle_event(
            session_data,
            "session_marked_inactive",
            source="chat_session_route.handle_chat_end_if_requested",
            detail="ユーザー操作によるチャット終了",
        )
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
    if should_skip_append_user_message(session, original_user_message):
        return
    user_msg = append_user_message(session, original_user_message)
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if session_data:
        session_data.setdefault("messages", [])
        if not should_skip_append_user_message(session_data, original_user_message):
            session_data["messages"].append(user_msg)
            session_data["last_activity"] = now_jst_iso()
            save_session_to_db(sid, session_data)
    else:
        save_session_to_db(
            sid,
            {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session.get("messages", []),
                "session_active": True,
                "last_activity": now_jst_iso(),
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
    if session.get("is_medicine_consultation", False):
        logger.info("📝 医薬品相談回答処理中のため、DB即時反映を完全にスキップ")
        return

    session_data = get_session_from_db(sid) or {}
    existing_messages = list(session_data.get("messages", []))
    session_messages = list(session.get("messages", []) or [])
    merged_messages = list(existing_messages)
    for new_msg in session_messages:
        if not any(
            ex.get("type") == new_msg.get("type")
            and ex.get("content") == new_msg.get("content")
            and ex.get("uuid") == new_msg.get("uuid")
            and ex.get("timestamp") == new_msg.get("timestamp")
            for ex in merged_messages
        ):
            merged_messages.append(new_msg)
    if not merged_messages:
        return
    ensure_session_persisted(
        sid,
        {
            "messages": merged_messages,
            "user_attributes": session.get("user_attributes", session_data.get("user_attributes", {})),
            "username": session.get("username") or session_data.get("username"),
            "session_active": True,
            "client_ip": getattr(client_info, "client_ip", None),
            "user_agent": getattr(client_info, "user_agent", None),
            "v2_local_test": session.get("v2_local_test", session_data.get("v2_local_test")),
            "v2_test_scenario": session.get("v2_test_scenario", session_data.get("v2_test_scenario")),
        },
        None,
    )


def apply_emotional_keyword_routing(
    session: Any,
    triage_result: Optional[Dict[str, Any]],
    sanitized_message: str,
    *,
    phase: str,
) -> Optional[str]:
    """
    眠気/不眠キーワードをセッションに記録（triage カテゴリは LLM 判定を維持）。
    phase: "sleepiness" | "insomnia"
    """
    from src.handlers.chat.chat_emotional_route import (
        detect_insomnia_keyword,
        detect_sleepiness_keyword,
    )

    if phase == "sleepiness":
        has_sleepiness = detect_sleepiness_keyword(sanitized_message)
        session["has_sleepiness_keyword"] = has_sleepiness
        if has_sleepiness:
            logger.info("🔍 眠気キーワードを検出（LLM トリアージは上書きしない）")
        return None

    has_sleepiness = session.get("has_sleepiness_keyword", False)
    has_insomnia = detect_insomnia_keyword(sanitized_message)
    session["has_insomnia_keyword"] = has_insomnia
    if has_insomnia and not has_sleepiness:
        logger.info("🔍 不眠キーワードを検出（LLM トリアージは上書きしない）")
    return None
