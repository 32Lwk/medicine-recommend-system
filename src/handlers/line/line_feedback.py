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
from src.services.feedback_trace import build_feedback_trace, submit_feedback_async
from src.services.session_manager import get_session_from_memory, touch_session_in_memory

logger = logging.getLogger(__name__)

POSTBACK_PREFIX = "mrcfb"
_PENDING_TTL_SEC = 86400  # 24h
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


def _get_database():
    from src.services.database import get_database

    return get_database()


def _db_usable(db) -> bool:
    if not db:
        return False
    if getattr(db, "startup_skip_reason", None) in ("connect_failed", "no_url", "no_driver"):
        return False
    return bool(db.is_available())


def _load_pending_map_from_db(sid: str) -> dict[str, Any]:
    db = _get_database()
    if not _db_usable(db):
        return {}
    raw = db.get_line_feedback_pending(sid)
    if not isinstance(raw, dict):
        return {}
    return _prune_pending(raw)


def _persist_pending_map(sid: str, pending: dict[str, Any]) -> None:
    pruned = _prune_pending(pending)
    by_sid = _pending_memory.setdefault(sid, {})
    by_sid.clear()
    by_sid.update(pruned)
    _pending_memory[sid] = by_sid

    session_data = get_session_from_memory(sid) or {"session_id": sid, "messages": []}
    session_data["line_feedback_pending"] = dict(pruned)
    touch_session_in_memory(sid, session_data)

    db = _get_database()
    if _db_usable(db):
        if pruned:
            db.set_line_feedback_pending(sid, pruned)
        else:
            db.set_line_feedback_pending(sid, None)


def _store_pending_entry(sid: str, key: str, entry: dict[str, Any]) -> None:
    pending = _load_pending_map(sid)
    pending[key] = entry
    _persist_pending_map(sid, pending)


def _load_pending_map(sid: str) -> dict[str, Any]:
    mem = _pending_memory.get(sid)
    if isinstance(mem, dict) and mem:
        return _prune_pending(mem)

    session_data = get_session_from_memory(sid) or {}
    session_pending = session_data.get("line_feedback_pending")
    if isinstance(session_pending, dict) and session_pending:
        pruned = _prune_pending(session_pending)
        _pending_memory[sid] = pruned
        return pruned

    db_pending = _load_pending_map_from_db(sid)
    if db_pending:
        _pending_memory[sid] = db_pending
        if session_data:
            session_data["line_feedback_pending"] = dict(db_pending)
            touch_session_in_memory(sid, session_data)
    return db_pending


def clear_line_feedback_pending(sid: str) -> None:
    """チャット終了などで評価 pending をすべて削除する。"""
    _pending_memory.pop(sid, None)
    session_data = get_session_from_memory(sid)
    if isinstance(session_data, dict):
        session_data.pop("line_feedback_pending", None)
        touch_session_in_memory(sid, session_data)
    db = _get_database()
    if _db_usable(db):
        db.set_line_feedback_pending(sid, None)


def register_line_feedback_pending(
    sid: str,
    *,
    user_message: str,
    ai_response: str,
) -> str:
    """評価用コンテキストを保存し、postback 用キーを返す（メモリ + DB 永続化）。"""
    key = _public_feedback_key()
    entry = {
        "user_message": (user_message or "")[:500],
        "ai_response": (ai_response or "")[:2000],
        "ts": time.time(),
    }
    _store_pending_entry(sid, key, entry)
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


def feedback_display_texts() -> frozenset[str]:
    """Quick Reply postback の displayText 一覧（全言語）。"""
    texts: set[str] = set()
    for lang in ("ja", "en", "ko", "zh"):
        ui = get_line_ui_strings(lang)
        for key in ("feedback_positive_display", "feedback_negative_display"):
            value = (ui.get(key) or "").strip()
            if value:
                texts.add(value)
    return frozenset(texts)


def is_line_feedback_display_text(text: str) -> bool:
    """postback の displayText が message イベントとして重複送信された場合 True。"""
    return (text or "").strip() in feedback_display_texts()


def _load_pending_context(sid: str, feedback_key: str) -> dict[str, str] | None:
    pending = _load_pending_map(sid)
    entry = pending.get(feedback_key)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("ts", 0)) > _PENDING_TTL_SEC:
        return None
    return {
        "user_message": str(entry.get("user_message") or ""),
        "ai_response": str(entry.get("ai_response") or ""),
    }


def _remove_pending_entry(sid: str, feedback_key: str) -> None:
    pending = _load_pending_map(sid)
    if feedback_key in pending:
        pending.pop(feedback_key, None)
        _persist_pending_map(sid, pending)


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
    from src.core.language_utils import resolve_session_language

    session = prime_line_session(user_id)
    lang = resolve_session_language(session)
    ui = get_line_ui_strings(lang)

    context = _load_pending_context(sid, feedback_key)
    if not context:
        # 期限切れ・別インスタンス再起動後の古いボタン等。ユーザーへの返信は出さない。
        logger.info(
            "LINE feedback postback ignored (no pending context): sid=%s key=%s",
            sid,
            feedback_key,
        )
        return

    username = session.get("username") or "LINEユーザー"
    trace = build_feedback_trace(
        source="line",
        event="feedback_postback",
        session_id=sid,
        line_user_id=user_id,
        report_type=report_type,
        feedback_key=feedback_key,
        language=lang,
        user_message_preview=(context["user_message"] or "")[:200],
    )
    submit_feedback_async(
        report_type=report_type,
        session_id=sid,
        username=username,
        user_message=context["user_message"],
        ai_response=context["ai_response"],
        feedback_text="LINE Quick Reply フィードバック",
        metadata=trace,
        dedupe=True,
    )
    _remove_pending_entry(sid, feedback_key)
    thank = ui.get("feedback_thank_you", "フィードバックありがとうございます！")

    if reply_token and LINE_CHANNEL_ACCESS_TOKEN:
        await reply_messages(reply_token, [{"type": "text", "text": thank}])
