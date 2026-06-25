"""
LINE 向け絵文字入力のトリアージ前ルート。

- 侮辱絵文字（テキスト併記含む）→ 長めの自己紹介（侮辱への言及なし）
- 絵文字のみ → 軽量 LLM 5 分類 → greeting/thanks/emotional/unknown
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.services.emoji_intent import (
    EmojiIntent,
    build_emoji_unknown_ack_text,
    classify_emoji_intent_llm,
    generate_offensive_emoji_response_llm,
)
from src.utils.emoji_input import contains_offensive_emoji, is_emoji_only_message

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _append_user_turn(session: Any, content: str) -> None:
    from src.utils.jst_datetime import now_jst_iso

    session.setdefault("messages", []).append(
        {
            "type": "user",
            "content": content,
            "timestamp": now_jst_iso(),
            "uuid": str(uuid.uuid4()),
        }
    )


def _append_text_bot(
    session: Any,
    sid: Optional[str],
    content: str,
    *,
    title: str,
    kind: str,
    concierge: bool = False,
    concierge_intent: Optional[str] = None,
    greeting: bool = False,
) -> None:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_concierge_text_status

    bot = build_bot_response(
        session,
        sid,
        legacy_content=content,
        sage_diagnosis=build_concierge_text_status(
            content, title=title, kind=kind
        ).to_client_dict(),
        concierge=concierge,
        concierge_intent=concierge_intent,
        content_format="text",
        uuid=str(uuid.uuid4()),
    )
    if greeting:
        bot["greeting"] = True
    session.setdefault("messages", []).append(bot)


def _append_dynamic_status_bot(
    session: Any,
    sid: Optional[str],
    *,
    body_text: str,
    title: str,
    kind: str,
    line_flex: dict[str, Any],
    content_html: str,
) -> None:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    bot = build_bot_response(
        session,
        sid,
        legacy_content=content_html,
        sage_diagnosis=build_notice_status(
            body_text,
            title=title,
            kind=kind,
            hints=["お体の不調やお薬のことがあれば、テキストでお聞かせください。"],
            show_feedback=False,
        ).to_client_dict(),
        concierge=True,
        content_format="status_card",
        uuid=str(uuid.uuid4()),
    )
    bot["line_flex"] = line_flex
    session.setdefault("messages", []).append(bot)


def _finish_offensive_emoji_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    recommendation_client: OpenAI,
) -> ResponseTuple:
    from src.services.concierge_templates import (
        build_dynamic_concierge_line_flex,
        format_dynamic_concierge_meta_card,
    )

    bot_text = generate_offensive_emoji_response_llm(
        recommendation_client,
        user_message,
        session_id=sid,
    )
    title = "お気持ち"
    hints = ["お体の不調やお薬のことがあれば、テキストでお聞かせください。"]
    line_flex = build_dynamic_concierge_line_flex(
        title=title,
        body_text=bot_text,
        hints=hints,
    )
    content_html = format_dynamic_concierge_meta_card(
        title=title,
        body_text=bot_text,
        hints=hints,
    )
    _append_user_turn(session, user_message)
    _append_dynamic_status_bot(
        session,
        sid,
        body_text=bot_text,
        title=title,
        kind="emoji_offensive_ack",
        line_flex=line_flex,
        content_html=content_html,
    )
    _log_emoji_plain_response(
        session,
        sid,
        user_message,
        bot_text,
        response_type="emoji_offensive_ack",
    )
    _mark_session_modified(session)
    _sync_session_db(session, client_info, sid)
    count = len(session.get("messages", []))
    return ({"status": "ok", "message_count": count}, 200)


def _sync_session_db(session: Any, client_info: Any, sid: Optional[str]) -> None:
    if not sid:
        return
    from src.handlers.line.line_session import is_line_session_id

    if not is_line_session_id(sid):
        from src.services.session_manager import get_session_from_db, save_session_to_db
        from src.utils.jst_datetime import now_jst_iso

        session_data = get_session_from_db(sid) or {
            "session_id": sid,
            "username": session.get("username", "Unknown"),
            "messages": [],
            "user_attributes": session.get("user_attributes", {}),
            "session_active": True,
        }
        session_data["messages"] = list(session.get("messages", []))
        session_data["last_activity"] = now_jst_iso()
        save_session_to_db(sid, session_data)
        return

    from src.handlers.chat.chat_concierge_route import _sync_session_db as sync_concierge_db

    sync_concierge_db(session, client_info, sid)


def _log_emoji_plain_response(
    session: Any,
    sid: Optional[str],
    user_message: str,
    bot_text: str,
    *,
    response_type: str,
) -> None:
    if not sid or not user_message or not bot_text:
        return
    try:
        from src.services.counseling.counseling_logger import log_counseling_response
        from src.services.line_memory_context import get_counseling_conversation_history

        log_counseling_response(
            session_id=sid,
            response_content=bot_text,
            response_type=response_type,
            category="Concierge",
            user_input=user_message,
            conversation_history=get_counseling_conversation_history(session, sid),
            session=session,
        )
    except Exception as exc:
        logger.debug("emoji route counseling log skipped: %s", exc)


def _finish_plain_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    bot_text: str,
    *,
    title: str,
    kind: str,
    concierge: bool = False,
    concierge_intent: Optional[str] = None,
) -> ResponseTuple:
    _append_user_turn(session, user_message)
    _append_text_bot(
        session,
        sid,
        bot_text,
        title=title,
        kind=kind,
        concierge=concierge,
        concierge_intent=concierge_intent,
    )
    _log_emoji_plain_response(
        session,
        sid,
        user_message,
        bot_text,
        response_type=kind,
    )
    _mark_session_modified(session)
    _sync_session_db(session, client_info, sid)
    count = len(session.get("messages", []))
    return ({"status": "ok", "message_count": count}, 200)


def _route_emoji_concierge(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    intent: str,
) -> Optional[ResponseTuple]:
    from src.handlers.chat.chat_concierge_route import try_concierge_response

    triage_result = {
        "category": "Other",
        "subcategory": "general_other",
        "confidence": 0.9,
        "concierge_intent": intent,
        "concierge_intent_source": "emoji_llm",
    }
    return try_concierge_response(
        session,
        client_info,
        sid,
        user_message,
        sanitized_message,
        triage_result,
        recommendation_client,
    )


def _route_emoji_emotional(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
) -> Optional[ResponseTuple]:
    from src.handlers.chat.chat_emotional_route import handle_emotional_category
    from src.services.session_manager import append_user_message

    append_user_message(session, user_message)
    triage_result = {
        "category": "Emotional",
        "subcategory": "general_emotional",
        "confidence": 0.9,
        "_emoji_intent": "emotional",
    }
    resp = handle_emotional_category(
        session,
        sid,
        user_message,
        sanitized_message,
        triage_result,
        recommendation_client,
    )
    if resp is None:
        return None
    _sync_session_db(session, client_info, sid)
    return resp


def _route_by_emoji_intent(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    intent: EmojiIntent,
) -> Optional[ResponseTuple]:
    if intent == "offensive":
        return _finish_offensive_emoji_response(
            session,
            client_info,
            sid,
            user_message,
            recommendation_client,
        )
    if intent in ("greeting", "thanks"):
        return _route_emoji_concierge(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
            intent,
        )
    if intent == "emotional":
        return _route_emoji_emotional(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
        )
    return _finish_plain_response(
        session,
        client_info,
        sid,
        user_message,
        build_emoji_unknown_ack_text(),
        title="ご案内",
        kind="emoji_unknown_ack",
        concierge=True,
        concierge_intent="redirect",
    )


def try_emoji_pre_triage_route(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
) -> Optional[ResponseTuple]:
    """
    LINE セッション向け絵文字ルート。該当しなければ None。
    挿入位置: run_triage の直前。
    """
    from src.handlers.line.line_session import is_line_session_id
    from src.services.pipeline_perf import mark_pipeline_step

    if not is_line_session_id(sid):
        return None

    text = (sanitized_message or user_message or "").strip()
    if not text:
        return None

    mark_pipeline_step("emoji_route_start")

    if contains_offensive_emoji(text):
        logger.info("🎭 emoji_route: offensive emoji detected (empathetic ack)")
        mark_pipeline_step("emoji_route_offensive")
        return _finish_offensive_emoji_response(
            session,
            client_info,
            sid,
            user_message,
            recommendation_client,
        )

    if not is_emoji_only_message(text):
        mark_pipeline_step("emoji_route_skip_not_emoji_only")
        return None

    mark_pipeline_step("emoji_intent_llm_start")
    intent, conf = classify_emoji_intent_llm(
        recommendation_client,
        text,
        session_id=sid,
    )
    mark_pipeline_step("emoji_intent_llm_end")
    logger.info("🎭 emoji_route: intent=%s confidence=%.2f", intent, conf)

    resp = _route_by_emoji_intent(
        session,
        client_info,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        intent,
    )
    if resp is not None:
        mark_pipeline_step("emoji_route_done")
    return resp
