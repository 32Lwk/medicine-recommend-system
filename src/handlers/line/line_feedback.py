"""
LINE Quick Reply + postback によるフィードバック（Web の /api/submit_feedback と同じ保存先）。
"""
from __future__ import annotations

import logging
import secrets
import time
from typing import Any

from src.handlers.line.flex_messages import html_to_plain_text
from src.handlers.line.line_i18n import get_line_ui_strings
from src.handlers.line.line_session import line_sid
from src.services.feedback_submit import FeedbackSubmitError, submit_feedback_record
from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

POSTBACK_PREFIX = "mrcfb"
_PENDING_TTL_SEC = 86400  # 24h（DB 未接続時もメモリで保持）
_MAX_PENDING = 20

# DB とメモリの不整合時でも postback を受け付けるプロセス内ストア
_pending_memory: dict[str, dict[str, dict[str, Any]]] = {}


def _public_feedback_key() -> str:
    return secrets.token_hex(4)


def _summarize_ai_response(bot_message: dict[str, Any], line_messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for msg in line_messages:
        if msg.get("type") == "flex":
            alt = str(msg.get("altText") or "").strip()
            if alt:
                parts.append(alt)
        elif msg.get("type") == "text":
            text = str(msg.get("text") or "").strip()
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts)[:2000]
    plain = html_to_plain_text(bot_message.get("content"))
    return plain[:2000] if plain else "LINE bot response"


def _prune_pending(pending: dict[str, Any]) -> dict[str, Any]:
    now = time.time()
    kept = {
        k: v
        for k, v in pending.items()
        if isinstance(v, dict) and now - float(v.get("ts", 0)) < _PENDING_TTL_SEC
    }
    if len(kept) > _MAX_PENDING:
        sorted_keys = sorted(kept, key=lambda k: float(kept[k].get("ts", 0)))
        for old_key in sorted_keys[: len(kept) - _MAX_PENDING]:
            kept.pop(old_key, None)
    return kept


def _store_pending_entry(sid: str, key: str, entry: dict[str, Any]) -> None:
    by_sid = _pending_memory.setdefault(sid, {})
    by_sid[key] = entry
    _pending_memory[sid] = _prune_pending(by_sid)


def register_line_feedback_pending(
    sid: str,
    *,
    user_message: str,
    ai_response: str,
) -> str:
    """評価用コンテキストを保存し、postback 用キーを返す（メモリ優先・DB は補助）。"""
    key = _public_feedback_key()
    entry = {
        "user_message": (user_message or "")[:500],
        "ai_response": (ai_response or "")[:2000],
        "ts": time.time(),
    }
    _store_pending_entry(sid, key, entry)

    session_data = get_session_from_db(sid) or {"session_id": sid, "messages": []}
    pending = session_data.get("line_feedback_pending") or {}
    if not isinstance(pending, dict):
        pending = {}
    pending[key] = dict(entry)
    session_data["line_feedback_pending"] = _prune_pending(pending)
    save_session_to_db(sid, session_data)
    return key


def build_feedback_quick_reply(feedback_key: str, ui: dict[str, str]) -> dict[str, Any]:
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": ui.get("feedback_positive_label", "👍 役に立った"),
                    "data": f"{POSTBACK_PREFIX}|pos|{feedback_key}",
                    "displayText": ui.get("feedback_positive_display", "役に立った"),
                },
            },
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": ui.get("feedback_negative_label", "👎 役に立たなかった"),
                    "data": f"{POSTBACK_PREFIX}|neg|{feedback_key}",
                    "displayText": ui.get("feedback_negative_display", "役に立たなかった"),
                },
            },
        ]
    }


def attach_feedback_quick_reply(
    line_messages: list[dict[str, Any]],
    feedback_key: str,
    ui: dict[str, str],
) -> list[dict[str, Any]]:
    """最後のメッセージに Quick Reply を付与する（コピーを返す）。"""
    if not line_messages or not feedback_key:
        return line_messages
    out = [dict(m) for m in line_messages]
    last = dict(out[-1])
    last["quickReply"] = build_feedback_quick_reply(feedback_key, ui)
    out[-1] = last
    return out


def prepare_line_messages_with_feedback(
    line_messages: list[dict[str, Any]],
    *,
    sid: str,
    user_message: str,
    bot_message: dict[str, Any],
    lang: str | None,
) -> list[dict[str, Any]]:
    if not line_messages:
        return line_messages
    ui = get_line_ui_strings(lang)
    ai_response = _summarize_ai_response(bot_message, line_messages)
    feedback_key = register_line_feedback_pending(
        sid,
        user_message=user_message,
        ai_response=ai_response,
    )
    return attach_feedback_quick_reply(line_messages, feedback_key, ui)


def parse_feedback_postback(data: str) -> tuple[str, str] | None:
    """postback data から (report_type, feedback_key) を返す。"""
    parts = (data or "").split("|")
    if len(parts) != 3 or parts[0] != POSTBACK_PREFIX:
        return None
    kind, key = parts[1], parts[2]
    if not key or len(key) > 32:
        return None
    if kind == "pos":
        return "positive_feedback", key
    if kind == "neg":
        return "negative_feedback", key
    return None


def _load_pending_context(sid: str, feedback_key: str) -> dict[str, str] | None:
    mem_entry = (_pending_memory.get(sid) or {}).get(feedback_key)
    if isinstance(mem_entry, dict):
        if time.time() - float(mem_entry.get("ts", 0)) <= _PENDING_TTL_SEC:
            return {
                "user_message": str(mem_entry.get("user_message") or ""),
                "ai_response": str(mem_entry.get("ai_response") or ""),
            }

    session_data = get_session_from_db(sid) or {}
    pending = session_data.get("line_feedback_pending") or {}
    if not isinstance(pending, dict):
        return None
    entry = pending.get(feedback_key)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("ts", 0)) > _PENDING_TTL_SEC:
        return None
    return {
        "user_message": str(entry.get("user_message") or ""),
        "ai_response": str(entry.get("ai_response") or ""),
    }


async def handle_line_feedback_postback(
    user_id: str,
    postback_data: str,
    *,
    reply_token: str | None,
) -> None:
    from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
    from src.handlers.line.line_reply import reply_messages
    from src.handlers.line.line_session import prime_line_session

    parsed = parse_feedback_postback(postback_data)
    ui = get_line_ui_strings("ja")
    if not parsed:
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(
                reply_token,
                [{"type": "text", "text": ui.get("feedback_submit_failed", "送信に失敗しました。")}],
            )
        return

    report_type, feedback_key = parsed
    sid = line_sid(user_id)
    session = prime_line_session(user_id)
    lang = session.get("detected_language") or "ja"
    ui = get_line_ui_strings(lang)

    context = _load_pending_context(sid, feedback_key)
    if not context:
        if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
            await reply_messages(
                reply_token,
                [{"type": "text", "text": ui.get("feedback_expired", "評価の有効期限が切れました。")}],
            )
        return

    username = session.get("username") or "LINEユーザー"
    try:
        submit_feedback_record(
            report_type=report_type,
            session_id=sid,
            username=username,
            user_message=context["user_message"],
            ai_response=context["ai_response"],
            dedupe=True,
        )
        thank = ui.get("feedback_thank_you", "フィードバックありがとうございます！")
    except FeedbackSubmitError as exc:
        if exc.status_code == 429:
            thank = ui.get("feedback_already_submitted", "すでに送信済みです。")
        else:
            logger.warning("LINE feedback submit failed: %s", exc)
            thank = ui.get("feedback_submit_failed", "送信に失敗しました。しばらくして再度お試しください。")

    if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
        await reply_messages(reply_token, [{"type": "text", "text": thank}])
