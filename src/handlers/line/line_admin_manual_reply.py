"""管理画面からの薬剤師手動返信を LINE ユーザーへ Push する。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
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
    session_data["last_activity"] = datetime.now()
    save_session_to_db(session_id, session_data)

    line_pushed: bool | None = None
    line_error: str | None = None
    if is_line_session_id(session_id):
        user_id = user_id_from_line_sid(session_id)
        if not user_id:
            line_pushed = False
            line_error = "invalid_line_session_id"
        elif not LINE_CHANNEL_ACCESS_TOKEN:
            line_pushed = False
            line_error = "LINE_CHANNEL_ACCESS_TOKEN not configured"
            logger.warning(
                "Admin manual reply saved but LINE push skipped (no token) sid=%s",
                session_id,
            )
        else:
            pushed = await push_messages(
                user_id,
                [{"type": "text", "text": text[:LINE_TEXT_MAX_LEN]}],
            )
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
