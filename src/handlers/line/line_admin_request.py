"""LINE / Web 共通の薬剤師要請・取消・AI 復帰。"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from src.handlers.line.line_i18n import get_line_ui_strings
from src.services.session_manager import (
    clear_admin_request_state,
    get_manual_reply_queue,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
    set_manual_reply_queue,
)

logger = logging.getLogger(__name__)

PHARMACIST_DISCLAIMER_JA = (
    "「薬剤師要請」は将来的な実装を想定したデモ機能であり、"
    "実際に薬剤師が応答・返信する体制が常時稼働しているわけではありません。"
    "それでも要請しますか？"
)


def _now_iso() -> str:
    return datetime.now().isoformat()


def _ensure_session_data(sid: str) -> dict[str, Any]:
    session_data = get_session_from_db(sid)
    if session_data:
        return session_data
    return {
        "session_id": sid,
        "username": f"ユーザー{get_next_user_number()}",
        "messages": [],
        "last_activity": datetime.now(),
        "user_attributes": {},
        "session_active": True,
    }


def is_pharmacist_request_pending(session_data: dict[str, Any] | None) -> bool:
    return bool(session_data and session_data.get("admin_request"))


def should_offer_return_to_ai(session_data: dict[str, Any] | None) -> bool:
    """薬剤師返信後など、手動モードのまま AI に戻せる状態。"""
    if not session_data:
        return False
    if session_data.get("admin_request"):
        return False
    if session_data.get("ai_auto_reply") is not False:
        return False
    messages = session_data.get("messages") or []
    return any(isinstance(m, dict) and m.get("manual_reply") for m in messages)


def request_pharmacist_for_session(
    sid: str,
    *,
    session_data: dict[str, Any] | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    """Web `/api/request_admin` と同等の要請処理。"""
    if not sid:
        return {"ok": False, "error": "no_session"}

    session_data = session_data or _ensure_session_data(sid)
    ui = get_line_ui_strings(lang)
    username = session_data.get("username", "unknown")
    session_data["admin_request"] = True
    session_data["ai_auto_reply"] = False

    content = ui.get(
        "pharmacist_requested_message",
        "薬剤師対応を要請しました。しばらくお待ちください。",
    )
    system_message = {
        "type": "bot",
        "content": content,
        "admin_request": True,
        "style_class": "admin-request",
        "timestamp": _now_iso(),
        "uuid": str(uuid.uuid4()),
    }
    session_data.setdefault("messages", [])
    session_data["messages"].append(system_message)
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)

    queue = get_manual_reply_queue()
    already_exists = any(
        item.get("session_id") == sid and item.get("admin_request") for item in queue
    )
    if not already_exists:
        queue.append(
            {
                "session_id": sid,
                "username": username,
                "user_message": "【薬剤師要請】" + username,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "admin_requested",
                "admin_request": True,
            }
        )
        set_manual_reply_queue(queue)

    logger.info("Pharmacist request registered sid=%s", sid)
    return {"ok": True, "session_data": session_data, "bot_message": system_message}


def cancel_pharmacist_request(
    sid: str,
    *,
    lang: str | None = None,
) -> dict[str, Any]:
    """要請待ち中の取消（Web の /clear 相当だが履歴は保持）。"""
    session_data = get_session_from_db(sid)
    if not session_data or not session_data.get("admin_request"):
        ui = get_line_ui_strings(lang)
        return {
            "ok": False,
            "error": "not_pending",
            "reply_text": ui.get("pharmacist_cancel_not_pending", "薬剤師要請は見つかりませんでした。"),
        }

    clear_admin_request_state(sid, session_data)
    ui = get_line_ui_strings(lang)
    content = ui.get(
        "pharmacist_cancelled_message",
        "薬剤師要請を取り消しました。引き続き AI がお答えします。",
    )
    bot_message = {
        "type": "bot",
        "content": content,
        "timestamp": _now_iso(),
        "uuid": str(uuid.uuid4()),
    }
    session_data.setdefault("messages", [])
    session_data["messages"].append(bot_message)
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)
    logger.info("Pharmacist request cancelled sid=%s", sid)
    return {"ok": True, "session_data": session_data, "bot_message": bot_message, "reply_text": content}


def return_session_to_ai(
    sid: str,
    *,
    lang: str | None = None,
) -> dict[str, Any]:
    """薬剤師返信後に AI 自動応答へ戻す。"""
    session_data = get_session_from_db(sid)
    if not session_data:
        ui = get_line_ui_strings(lang)
        return {
            "ok": False,
            "error": "not_found",
            "reply_text": ui.get("pharmacist_return_not_available", "操作できませんでした。"),
        }
    if session_data.get("admin_request"):
        ui = get_line_ui_strings(lang)
        return {
            "ok": False,
            "error": "still_pending",
            "reply_text": ui.get(
                "pharmacist_return_still_pending",
                "薬剤師確認中です。取り消す場合は「要請を取り消す」を選んでください。",
            ),
        }

    session_data["ai_auto_reply"] = True
    clear_admin_request_state(sid, session_data)
    ui = get_line_ui_strings(lang)
    content = ui.get(
        "pharmacist_return_ai_message",
        "AI 自動応答に戻しました。症状やご質問をお送りください。",
    )
    bot_message = {
        "type": "bot",
        "content": content,
        "timestamp": _now_iso(),
        "uuid": str(uuid.uuid4()),
    }
    session_data.setdefault("messages", [])
    session_data["messages"].append(bot_message)
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)
    logger.info("Session returned to AI sid=%s", sid)
    return {"ok": True, "session_data": session_data, "bot_message": bot_message, "reply_text": content}


def clear_admin_request_after_manual_reply(session_id: str) -> None:
    """薬剤師が手動返信したあと、要請待ちフラグだけ解除する。"""
    session_data = get_session_from_db(session_id)
    if not session_data:
        return
    if session_data.get("admin_request"):
        session_data.pop("admin_request", None)
        queue = get_manual_reply_queue()
        filtered = [
            item
            for item in queue
            if not (
                str(item.get("session_id")) == str(session_id) and item.get("admin_request")
            )
        ]
        if len(filtered) != len(queue):
            set_manual_reply_queue(filtered)
        save_session_to_db(session_id, session_data)
