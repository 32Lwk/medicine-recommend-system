"""
Emotional カテゴリのチャット分岐（カウンセリング開始）

chat_handler から移行した完全版（不眠/眠気の医薬品案内メッセージ・初期質問ログ含む）
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

SLEEPINESS_KEYWORDS = [
    "寝てしまう", "眠くて寝てしまう", "眠すぎて寝てしまう",
    "仕事中に寝てしまう", "居眠り", "眠くてたまらない",
    "眠気に襲われる", "眠くて仕方がない", "眠すぎる",
    "眠気が強い", "眠い", "眠たい", "寝むたい", "寝たい", "眠気", "だるい", "いつも眠い",
    "眠くて", "眠すぎ", "眠気で", "眠気です", "眠気が", "眠気の",
    "日中の眠気", "昼間の眠気", "眠くて困る", "眠くて仕方ない",
    "眠気が取れない", "眠気が強い", "強い眠気", "眠気がひどい",
    "日中に寝てしまう", "日中に寝てしま", "日中寝てしまう", "日中寝てしま",
]

INSOMNIA_KEYWORDS = [
    "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠れません", "眠れないです",
    "眠れない", "夜眠れない", "最近眠れない", "最近眠れません", "夜眠れません",
    "寝れない", "寝れません", "寝れないです", "夜寝れない", "最近寝れない",
    "眠れなくて", "眠れなく", "寝つけない", "寝つけません", "寝つけないです",
    "不眠で", "不眠です", "不眠の", "不眠が",
    "睡眠薬", "睡眠薬を", "睡眠薬について", "睡眠薬を教えて", "睡眠薬を知りたい",
    "睡眠改善薬", "睡眠改善薬を", "睡眠改善薬について", "睡眠改善薬を教えて",
    "睡眠薬を紹介", "睡眠薬を紹介して", "睡眠改善薬を紹介", "睡眠改善薬を紹介して",
]

INSOMNIA_MEDICINE_INFO = "一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。"
DROWSINESS_MEDICINE_INFO = "眠気で、推奨される医薬品を知りたい場合は教えて下さい。"


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def detect_sleepiness_keyword(message: str) -> bool:
    return any(kw in (message or "") for kw in SLEEPINESS_KEYWORDS)


def detect_insomnia_keyword(message: str) -> bool:
    return any(kw in (message or "") for kw in INSOMNIA_KEYWORDS)


def _append_counseling_medicine_info(
    session: Any,
    sid: Optional[str],
    user_message: str,
    category: str,
    confidence: float,
    message_text: str,
    *,
    log_counseling_response,
) -> None:
    from src.services.sage_bot_response import build_counseling_bot

    for msg in session.get("messages", []):
        if (
            msg.get("type") == "bot"
            and msg.get("counseling_medicine_info")
            and msg.get("content") == message_text
        ):
            logger.info("⏭️ 既に医薬品情報メッセージが存在するため、追加をスキップします")
            return

    session.setdefault("messages", []).append(
        build_counseling_bot(
            session,
            sid,
            message_text,
            title="カウンセリング",
            kind="counseling_medicine_info",
            counseling=True,
            counseling_medicine_info=True,
        )
    )
    _mark_session_modified(session)
    log_counseling_response(
        session_id=sid,
        response_content=message_text,
        response_type="counseling_medicine_info",
        category=category,
        confidence=confidence,
        counseling_mode=session.get("counseling_mode"),
        user_input=user_message,
        conversation_history=None,
    )


def handle_emotional_category(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Optional[Dict[str, Any]],
    recommendation_client: OpenAI,
    *,
    has_sleepiness_keyword: bool = False,
    has_insomnia_keyword: bool = False,
) -> Optional[ResponseTuple]:
    """
    Emotional カテゴリのカウンセリング開始（完全版）。
    処理した場合は (dict, status)、未処理・エラー継続は None。
    """
    if not triage_result:
        triage_result = {"category": "Emotional", "confidence": 1.0}

    category = triage_result.get("category", "Emotional")
    if category != "Emotional":
        return None

    confidence = float(triage_result.get("confidence", 1.0))
    subcategory_lower = (triage_result.get("subcategory") or "").lower()

    try:
        from src.services.counseling_response import (
            detect_emotional_symptom_type,
            generate_counseling_response,
            generate_follow_up_questions,
            log_counseling_response,
            start_counseling_mode,
        )

        symptom_type = detect_emotional_symptom_type(sanitized_message, triage_result)

        if has_sleepiness_keyword and symptom_type != "drowsiness":
            symptom_type = "drowsiness"
            logger.info("🔄 眠気関連キーワード直接検出により、symptom_typeを'drowsiness'に変更しました")

        if has_insomnia_keyword and symptom_type != "insomnia" and not has_sleepiness_keyword:
            symptom_type = "insomnia"
            logger.info("🔄 不眠関連キーワード直接検出により、symptom_typeを'insomnia'に変更しました")

        from src.services.line_memory_context import get_counseling_conversation_history

        conversation_history = get_counseling_conversation_history(session, sid)

        initial_response = generate_counseling_response(
            symptom_type,
            user_message,
            recommendation_client,
            conversation_history=conversation_history,
            session_id=sid,
        )
        initial_questions = generate_follow_up_questions(symptom_type, {}, recommendation_client)
        start_counseling_mode(session, symptom_type, initial_questions)

        first_question = initial_questions[0] if initial_questions else None
        if first_question:
            counseling_mode = session.setdefault("counseling_mode", {})
            counseling_mode.setdefault("question_history", []).append({
                "question": first_question,
                "asked_at": datetime.now().isoformat(),
                "question_type": "initial",
            })

        from src.services.counseling.counseling_format import combine_counseling_message
        from src.services.sage_bot_response import build_counseling_bot

        session.setdefault("messages", []).append(
            build_counseling_bot(
                session,
                sid,
                combine_counseling_message(initial_response, first_question),
                title="カウンセリング",
                kind="counseling_initial",
                counseling=True,
                counseling_question=bool(first_question),
            )
        )

        log_counseling_response(
            session_id=sid,
            response_content=initial_response,
            response_type="counseling_initial_response",
            category=category,
            confidence=confidence,
            counseling_mode=session.get("counseling_mode"),
            user_input=user_message,
            conversation_history=None,
        )

        is_insomnia_counseling = (
            symptom_type == "insomnia"
            or subcategory_lower == "insomnia"
            or "insomnia" in subcategory_lower
            or has_insomnia_keyword
        )
        if is_insomnia_counseling:
            if symptom_type != "insomnia":
                symptom_type = "insomnia"
                if session.get("counseling_mode"):
                    session["counseling_mode"]["symptom_type"] = "insomnia"
                logger.info("🔄 不眠関連キーワード検出により、symptom_typeを'insomnia'に変更しました")
            _append_counseling_medicine_info(
                session,
                sid,
                user_message,
                category,
                confidence,
                INSOMNIA_MEDICINE_INFO,
                log_counseling_response=log_counseling_response,
            )
            logger.info(
                "✅ 不眠カウンセリング開始: 医薬品情報メッセージ (symptom_type=%s, subcategory=%s)",
                symptom_type,
                triage_result.get("subcategory", "N/A"),
            )

        is_sleepiness_counseling = (
            symptom_type == "drowsiness"
            or subcategory_lower == "drowsiness"
            or "drowsiness" in subcategory_lower
            or has_sleepiness_keyword
        )
        if is_sleepiness_counseling:
            if symptom_type != "drowsiness":
                symptom_type = "drowsiness"
                if session.get("counseling_mode"):
                    session["counseling_mode"]["symptom_type"] = "drowsiness"
                logger.info("🔄 眠気関連キーワード検出により、symptom_typeを'drowsiness'に変更しました")
            _append_counseling_medicine_info(
                session,
                sid,
                user_message,
                category,
                confidence,
                DROWSINESS_MEDICINE_INFO,
                log_counseling_response=log_counseling_response,
            )
            logger.info(
                "✅ 眠気カウンセリング開始: 医薬品情報メッセージ (symptom_type=%s, subcategory=%s)",
                symptom_type,
                triage_result.get("subcategory", "N/A"),
            )

        if initial_questions:
            first_question = initial_questions[0]
            log_counseling_response(
                session_id=sid,
                response_content=first_question,
                response_type="counseling_initial_question",
                category=category,
                confidence=confidence,
                counseling_mode=session.get("counseling_mode"),
            )

        _mark_session_modified(session)
        if sid:
            from src.services.session_manager import get_session_from_db, save_session_to_db

            session_data = get_session_from_db(sid)
            if session_data:
                session_data["messages"] = session["messages"].copy()
                session_data["last_activity"] = datetime.now()
                session_data["counseling_mode"] = session.get("counseling_mode")
                save_session_to_db(sid, session_data)

        message_count = len(session.get("messages", []))
        logger.info("✅ カウンセリングフロー開始: %s messages", message_count)
        return ({"status": "ok", "message_count": message_count}, 200)

    except ImportError as e:
        logger.warning("⚠️ カウンセリングフロー機能のインポートに失敗: %s", e)
        return None
    except Exception as e:
        logger.error("❌ カウンセリングフロー機能でエラー: %s", e)
        traceback.print_exc()
        return None
