"""
Other カテゴリ（店舗非該当）— 不明要求カウンセリング・妊娠/授乳属性抽出
"""
from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.core.language_utils import update_session_language_from_message
from src.services.session_manager import (
    append_user_message,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
    was_last_user_message,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _extract_pregnancy_breastfeeding_from_other(session: Any, sanitized_message: str) -> None:
    if "user_attributes" not in session:
        session["user_attributes"] = {}
    user_attributes = session["user_attributes"]
    msg_for_attr = sanitized_message
    if "妊娠" in msg_for_attr or "pregnant" in msg_for_attr.lower():
        if any(
            kw in msg_for_attr
            for kw in ["妊娠していません", "妊娠中ではありません", "妊娠していない", "妊娠してない"]
        ):
            user_attributes["pregnant"] = False
            logger.info("📝 妊娠状態を登録（Otherフロー）: False")
        elif any(
            kw in msg_for_attr
            for kw in [
                "妊娠中です", "妊娠中", "妊娠しています", "妊娠しました",
                "妊娠してます", "妊娠した", "妊婦です",
            ]
        ):
            user_attributes["pregnant"] = True
            logger.info("📝 妊娠状態を登録（Otherフロー）: True")
    if "授乳" in msg_for_attr or "breastfeeding" in msg_for_attr.lower():
        if any(
            kw in msg_for_attr
            for kw in ["授乳していません", "授乳中ではありません", "授乳していない"]
        ):
            user_attributes["breastfeeding"] = False
            logger.info("📝 授乳状態を登録（Otherフロー）: False")
        elif any(
            kw in msg_for_attr
            for kw in ["授乳中です", "授乳中", "授乳しています", "授乳しました", "授乳してます"]
        ):
            user_attributes["breastfeeding"] = True
            logger.info("📝 授乳状態を登録（Otherフロー）: True")
    _mark_session_modified(session)


def _sync_user_message_to_db(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_msg: dict,
) -> None:
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if session_data:
        session_data.setdefault("messages", [])
        if not was_last_user_message(session_data, user_msg.get("content", "")):
            session_data["messages"].append(user_msg)
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)
    else:
        save_session_to_db(
            sid,
            {
                "session_id": sid,
                "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                "messages": [user_msg],
                "session_active": True,
                "last_activity": datetime.now(),
                "client_ip": client_info.client_ip,
                "user_agent": client_info.user_agent,
                "user_attributes": session.get("user_attributes", {}),
            },
        )


def _ensure_user_message_for_counseling(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    original_user_message: str,
) -> None:
    """カウンセリング判定の前に user を追記（再送時も履歴に残す）。"""
    if was_last_user_message(session, original_user_message):
        return
    user_msg = append_user_message(session, original_user_message)
    _sync_user_message_to_db(session, client_info, sid, user_msg)
    _mark_session_modified(session)


def run_other_unknown_counseling(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    processed_message: str,
    original_user_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
) -> Optional[ResponseTuple]:
    """
    店舗案内でない Other 向け不明要求カウンセリング。
    成功時は応答 tuple、失敗時は should_handle_other_category を立てて None。
    """
    from src.agents.concierge_agent import should_concierge_handle

    check_text = (sanitized_message or original_user_message or "").strip()
    if should_concierge_handle(
        check_text,
        triage_result,
        alt_texts=[original_user_message, user_message, processed_message],
    ):
        logger.info("⏭️ Concierge 対象のため不明要求カウンセリングをスキップ")
        return None

    logger.info("🔍 店舗案内ではないと判定されたため、カウンセリングフローに流す")
    _ensure_user_message_for_counseling(
        session, client_info, sid, original_user_message
    )
    if sid:
        try:
            from src.services.processing_status import set_processing_flow

            set_processing_flow(sid, "other_counseling")
        except Exception:
            pass
    try:
        _extract_pregnancy_breastfeeding_from_other(session, sanitized_message)
    except Exception as e:
        logger.warning("⚠️ Otherフローでの妊娠・授乳抽出でエラー: %s", e)

    try:
        from src.services.counseling_response import (
            generate_counseling_response,
            generate_follow_up_questions,
            has_specific_symptom,
            log_counseling_response,
            start_counseling_mode,
        )

        symptom_type = "inappropriate_request/unknown"
        from src.services.line_memory_context import get_counseling_conversation_history

        conversation_history = get_counseling_conversation_history(session, sid)
        initial_response = generate_counseling_response(
            symptom_type,
            original_user_message,
            recommendation_client,
            conversation_history=conversation_history,
            session_id=sid,
        )
        detected_language = update_session_language_from_message(session, original_user_message)
        if detected_language != "ja" and initial_response:
            try:
                from src.core.translation_service import translate_medicine_recommendation

                translated = translate_medicine_recommendation(
                    initial_response, detected_language, recommendation_client, session_id=sid
                )
                if translated and translated != initial_response:
                    initial_response = translated
                    logger.info("✅ カウンセリング返信翻訳完了: %s", detected_language)
            except Exception as e:
                logger.warning("⚠️ カウンセリング返信の翻訳エラー（日本語で返却）: %s", e)

        initial_questions = generate_follow_up_questions(symptom_type, {}, recommendation_client)
        start_counseling_mode(session, symptom_type, initial_questions)

        from src.services.sage_bot_response import build_counseling_bot

        bot_response = build_counseling_bot(
            session,
            sid,
            initial_response,
            title="カウンセリング",
            kind="counseling_unknown_request",
            counseling=True,
            inappropriate_request=True,
            request_type="unknown",
            uuid=str(uuid.uuid4()),
        )
        session.setdefault("messages", []).append(bot_response)

        if sid:
            session_data = get_session_from_db(sid) or {}
            session_data["messages"] = list(session.get("messages") or [])
            session_data["last_activity"] = datetime.now()
            session_data["user_attributes"] = session.get(
                "user_attributes", session_data.get("user_attributes", {})
            )
            save_session_to_db(sid, session_data)

        log_counseling_response(
            session_id=sid,
            response_content=initial_response,
            response_type="counseling_unknown_request",
            category="Other",
            confidence=triage_result.get("confidence", 0.5),
            counseling_mode=session.get("counseling_mode"),
            user_input=user_message,
            conversation_history=conversation_history,
        )
        _mark_session_modified(session)
        message_count = len(session["messages"])
        logger.info("✅ 不明な要求のカウンセリングフロー処理完了: %s messages", message_count)
        return ({"status": "ok", "message_count": message_count}, 200)

    except ImportError as e:
        logger.warning("⚠️ カウンセリングフロー機能のインポートに失敗: %s", e)
    except Exception as e:
        logger.error("❌ カウンセリングフロー処理でエラー: %s", e)
        traceback.print_exc()
        session["should_handle_other_category"] = True

    return None
