"""LINE Quick Reply — 薬剤師要請の取消 / AI 復帰。"""
from __future__ import annotations

from typing import Any

from src.handlers.line.line_admin_request import (
    is_pharmacist_request_pending,
    should_offer_return_to_ai,
)
from src.handlers.line.line_i18n import get_line_ui_strings

POSTBACK_PREFIX = "mrcmenu"


def build_cancel_pharmacist_quick_reply(ui: dict[str, str]) -> dict[str, Any]:
    label = ui.get("pharmacist_cancel_label", "要請を取り消す")
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": label,
                    "data": f"{POSTBACK_PREFIX}|pharmacist_cancel",
                    "displayText": label,
                },
            }
        ]
    }


def build_return_ai_quick_reply(ui: dict[str, str]) -> dict[str, Any]:
    label = ui.get("pharmacist_return_ai_label", "AI自動応答に戻す")
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": label,
                    "data": f"{POSTBACK_PREFIX}|return_ai",
                    "displayText": label,
                },
            }
        ]
    }


def build_delete_memory_quick_reply(ui: dict[str, str]) -> dict[str, Any]:
    yes_label = ui.get("memory_delete_confirm_yes", "削除する")
    no_label = ui.get("memory_delete_confirm_no", "キャンセル")
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": yes_label,
                    "data": f"{POSTBACK_PREFIX}|memory_delete_confirm|yes",
                    "displayText": yes_label,
                },
            },
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": no_label,
                    "data": f"{POSTBACK_PREFIX}|memory_delete_cancel",
                    "displayText": no_label,
                },
            },
        ]
    }


def attach_session_quick_actions(
    line_messages: list[dict[str, Any]],
    session_data: dict[str, Any] | None,
    *,
    lang: str | None,
) -> list[dict[str, Any]]:
    """最後のメッセージに、セッション状態に応じた Quick Reply を付与。"""
    if not line_messages or not session_data:
        return line_messages
    ui = get_line_ui_strings(lang)
    quick_reply = None
    if session_data.get("pending_memory_delete"):
        quick_reply = build_delete_memory_quick_reply(ui)
    elif is_pharmacist_request_pending(session_data):
        quick_reply = build_cancel_pharmacist_quick_reply(ui)
    elif should_offer_return_to_ai(session_data):
        quick_reply = build_return_ai_quick_reply(ui)
    if not quick_reply:
        return line_messages
    out = [dict(m) for m in line_messages]
    last = dict(out[-1])
    last["quickReply"] = quick_reply
    out[-1] = last
    return out
