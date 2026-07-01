"""LINE 配信アダプタ — ResponseEnvelope.line_messages 構築（Wave 1a）。"""
from __future__ import annotations

from typing import Any

from config.llm_flags import is_chat_pipeline_v2_for_session
from src.dialogue.envelope import ENVELOPE_SESSION_KEY, ResponseEnvelope


def build_line_delivery_envelope(
    bot_message: dict[str, Any],
    session: dict[str, Any],
    sid: str,
    lang: str,
) -> ResponseEnvelope:
    from src.handlers.line.flex_messages import build_line_messages_from_bot_message
    from src.handlers.line.line_quick_actions import attach_session_quick_actions

    line_messages = build_line_messages_from_bot_message(
        bot_message,
        lang=lang,
        session_id=sid,
    )
    line_messages = attach_session_quick_actions(line_messages, session, lang=lang)
    return ResponseEnvelope(
        delivery_mode="line_chunked",
        body={
            "status": "ok",
            "message_count": len(session.get("messages") or []),
        },
        status_code=200,
        line_messages=line_messages,
    )


def resolve_line_messages(
    bot_message: dict[str, Any],
    session: dict[str, Any],
    sid: str,
    lang: str,
) -> list[dict[str, Any]]:
    """
    LINE 送信用メッセージを解決する。
    v2 ON 時は Envelope を session に記録してから line_messages を返す。
    """
    envelope = build_line_delivery_envelope(bot_message, session, sid, lang)
    if is_chat_pipeline_v2_for_session(sid):
        session[ENVELOPE_SESSION_KEY] = envelope.to_session_dict()
    return list(envelope.line_messages)


def should_skip_redirect_on_missing_bot(session: dict[str, Any]) -> bool:
    """fail-loud（pipeline_end_guard=missing）時は redirect 補完をスキップ。"""
    return session.get("_pipeline_end_guard") == "missing"
