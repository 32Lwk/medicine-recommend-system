"""リッチメニュー・Quick Reply の postback 処理。"""
from __future__ import annotations

import logging
from typing import Any

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
from src.handlers.line.flex_messages import (
    PRIMARY,
    _public_site_base,
    build_web_continue_flex,
)
from src.handlers.line.line_admin_request import (
    PHARMACIST_DISCLAIMER_JA,
    cancel_pharmacist_request,
    request_pharmacist_for_session,
    return_session_to_ai,
)
from src.handlers.line.line_i18n import get_line_ui_strings
from src.handlers.line.line_quick_actions import (
    POSTBACK_PREFIX,
    attach_session_quick_actions,
)
from src.handlers.line.line_reply import push_messages, reply_messages
from src.handlers.line.line_session import line_sid, persist_line_session, prime_line_session
from src.core.language_utils import resolve_session_language
from src.services.session_manager import get_session_from_db

logger = logging.getLogger(__name__)

MENU_ACTIONS = frozenset(
    {
        "web_detail",
        "pharmacist",
        "pharmacist_confirm",
        "pharmacist_cancel",
        "pharmacist_cancel_request",
        "return_ai",
    }
)


def parse_menu_postback(data: str) -> tuple[str, str] | None:
    parts = (data or "").split("|")
    if len(parts) < 2 or parts[0] != POSTBACK_PREFIX:
        return None
    action = parts[1].strip()
    if action not in MENU_ACTIONS:
        return None
    extra = parts[2].strip() if len(parts) > 2 else ""
    return action, extra


def menu_display_texts() -> frozenset[str]:
    texts: set[str] = set()
    for lang in ("ja", "en", "ko", "zh"):
        ui = get_line_ui_strings(lang)
        for key in (
            "pharmacist_cancel_label",
            "pharmacist_return_ai_label",
            "pharmacist_confirm_yes",
            "pharmacist_confirm_no",
        ):
            value = (ui.get(key) or "").strip()
            if value:
                texts.add(value)
    return frozenset(texts)


def is_line_menu_display_text(text: str) -> bool:
    return (text or "").strip() in menu_display_texts()


def _pharmacist_confirm_flex(ui: dict[str, str]) -> dict[str, Any]:
    title = ui.get("pharmacist_confirm_title", "薬剤師に相談")
    body = ui.get("pharmacist_confirm_body", PHARMACIST_DISCLAIMER_JA)
    yes_label = ui.get("pharmacist_confirm_yes", "要請する")
    no_label = ui.get("pharmacist_confirm_no", "キャンセル")
    return {
        "type": "flex",
        "altText": title,
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "14px",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": body,
                        "size": "xs",
                        "wrap": True,
                        "color": "#666666",
                        "margin": "sm",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "height": "sm",
                                "color": PRIMARY,
                                "action": {
                                    "type": "postback",
                                    "label": yes_label,
                                    "data": f"{POSTBACK_PREFIX}|pharmacist_confirm|yes",
                                    "displayText": yes_label,
                                },
                                "flex": 1,
                            },
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "action": {
                                    "type": "postback",
                                    "label": no_label,
                                    "data": f"{POSTBACK_PREFIX}|pharmacist_cancel",
                                    "displayText": no_label,
                                },
                                "flex": 1,
                            },
                        ],
                    },
                ],
            },
        },
    }


async def _reply_messages(
    user_id: str,
    messages: list[dict[str, Any]],
    *,
    reply_token: str | None,
) -> None:
    if not LINE_CHANNEL_ACCESS_TOKEN or not messages:
        return
    if reply_token:
        await reply_messages(reply_token, messages)
    else:
        await push_messages(user_id, messages)


async def handle_line_menu_postback(
    user_id: str,
    postback_data: str,
    *,
    reply_token: str | None,
) -> bool:
    """リッチメニュー / Quick Reply の postback を処理。処理した場合 True。"""
    parsed = parse_menu_postback(postback_data)
    if not parsed:
        return False

    action, extra = parsed
    sid = line_sid(user_id)
    session = prime_line_session(user_id)
    lang = resolve_session_language(session)
    ui = get_line_ui_strings(lang)

    if action == "web_detail":
        from src.handlers.line.line_web_handoff import issue_handoff_token

        token = issue_handoff_token(sid)
        if not token:
            await _reply_messages(
                user_id,
                [{"type": "text", "text": ui.get("web_handoff_failed", "引き継ぎを開始できませんでした。")}],
                reply_token=reply_token,
            )
            persist_line_session(sid, session)
            return True
        resume_url = f"{_public_site_base()}/resume/{token}"
        await _reply_messages(
            user_id,
            [build_web_continue_flex(resume_url, ui)],
            reply_token=reply_token,
        )
        persist_line_session(sid, session)
        return True

    if action == "pharmacist":
        await _reply_messages(user_id, [_pharmacist_confirm_flex(ui)], reply_token=reply_token)
        persist_line_session(sid, session)
        return True

    if action == "pharmacist_cancel":
        await _reply_messages(
            user_id,
            [{"type": "text", "text": ui.get("pharmacist_confirm_aborted", "キャンセルしました。")}],
            reply_token=reply_token,
        )
        persist_line_session(sid, session)
        return True

    if action == "pharmacist_confirm" and extra == "yes":
        session_data = get_session_from_db(sid)
        result = request_pharmacist_for_session(sid, session_data=session_data, lang=lang)
        if not result.get("ok"):
            await _reply_messages(
                user_id,
                [{"type": "text", "text": ui.get("pharmacist_request_failed", "要請に失敗しました。")}],
                reply_token=reply_token,
            )
            persist_line_session(sid, session)
            return True
        messages = attach_session_quick_actions(
            [{"type": "text", "text": result["bot_message"]["content"]}],
            result["session_data"],
            lang=lang,
        )
        await _reply_messages(user_id, messages, reply_token=reply_token)
        persist_line_session(sid, session)
        return True

    if action == "pharmacist_cancel_request":
        result = cancel_pharmacist_request(sid, lang=lang)
        text = result.get("reply_text") or ui.get("pharmacist_cancelled_message", "")
        await _reply_messages(user_id, [{"type": "text", "text": text}], reply_token=reply_token)
        persist_line_session(sid, session)
        return True

    if action == "return_ai":
        result = return_session_to_ai(sid, lang=lang)
        text = result.get("reply_text") or ui.get("pharmacist_return_ai_message", "")
        await _reply_messages(user_id, [{"type": "text", "text": text}], reply_token=reply_token)
        persist_line_session(sid, session)
        return True

    return False
