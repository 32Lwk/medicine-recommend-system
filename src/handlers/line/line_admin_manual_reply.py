"""管理画面からの薬剤師手動返信を LINE ユーザーへ Push する。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from config.line_config import get_line_channel_access_token
from src.handlers.line.line_reply import push_messages
from src.handlers.line.line_session import is_line_session_id, user_id_from_line_sid
from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

LINE_TEXT_MAX_LEN = 5000


def _build_manual_reply_message(content: str) -> dict[str, Any]:
    return {
        "type": "bot",
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "manual_reply": True,
    }


async def apply_admin_manual_reply(session_id: str, message: str) -> dict[str, Any]:
    """
    セッション履歴に薬剤師返信を保存し、LINE セッションなら Push も行う。

    Returns:
        ok, target_session_id, line_pushed (bool|None), line_error (str|None)
    """
    text = (message or "").strip()
    if not session_id or not text:
        return {"ok": False, "error": "session_id and message are required"}

    session_data = get_session_from_db(session_id)
    if not session_data:
        return {"ok": False, "error": "session not found"}

    manual_reply = _build_manual_reply_message(text)
    session_data.setdefault("messages", [])
    session_data["messages"].append(manual_reply)
    from src.services.session_lifecycle import merge_messages_into_archive
    from src.utils.admin_timestamp import sync_last_activity_from_messages

    merge_messages_into_archive(session_data, [manual_reply])
    sync_last_activity_from_messages(session_data)
    save_session_to_db(session_id, session_data)

    from src.handlers.line.line_admin_request import clear_admin_request_after_manual_reply

    clear_admin_request_after_manual_reply(session_id)
    session_data = get_session_from_db(session_id) or session_data

    line_pushed: bool | None = None
    line_error: str | None = None
    if is_line_session_id(session_id):
        user_id = user_id_from_line_sid(session_id)
        if not user_id:
            line_pushed = False
            line_error = "invalid_line_session_id"
        elif not get_line_channel_access_token():
            line_pushed = False
            line_error = "LINE_CHANNEL_ACCESS_TOKEN not configured"
            logger.warning(
                "Admin manual reply saved but LINE push skipped (no token) sid=%s",
                session_id,
            )
        else:
            from src.core.language_utils import resolve_session_language
            from src.handlers.line.line_quick_actions import attach_session_quick_actions

            lang = resolve_session_language(session_data)
            push_payload = [{"type": "text", "text": text[:LINE_TEXT_MAX_LEN]}]
            push_payload = attach_session_quick_actions(
                push_payload,
                get_session_from_db(session_id),
                lang=lang,
            )
            pushed = await push_messages(user_id, push_payload)
            line_pushed = pushed
            if not pushed:
                line_error = "line_push_failed"
                logger.warning(
                    "Admin manual reply saved but LINE push failed sid=%s userId=%s",
                    session_id,
                    user_id,
                )
            else:
                logger.info(
                    "Admin manual reply pushed to LINE sid=%s userId=%s",
                    session_id,
                    user_id,
                )

    return {
        "ok": True,
        "target_session_id": session_id,
        "line_pushed": line_pushed,
        "line_error": line_error,
    }
