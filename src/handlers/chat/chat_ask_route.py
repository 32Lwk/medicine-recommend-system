"""
Ask カテゴリ — 推奨医薬品 Q&A・不眠/眠気カウンセリングからの薬推奨遷移
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

SLEEP_MEDICINE_KEYWORDS = [
    "睡眠薬", "睡眠薬を", "睡眠薬について", "睡眠薬を教えて", "睡眠薬を知りたい",
    "睡眠改善薬", "睡眠改善薬を", "睡眠改善薬について", "睡眠改善薬を教えて",
]


@dataclass
class AskRouteState:
    """Ask 分岐後の状態（Physical へ fall-through する場合あり）"""

    response: Optional[ResponseTuple] = None
    category: str = "Ask"
    sanitized_message: str = ""
    user_message: str = ""
    is_question: Optional[bool] = None
    triage_result: Optional[Dict[str, Any]] = None


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def handle_ask_category(
    session: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: OpenAI,
    recommended_medicines: List[Dict[str, Any]],
    medicine_list: List[Dict[str, Any]],
) -> Optional[ResponseTuple]:
    """推奨医薬品コンテキストでの Q&A（既存 API）"""
    from src.agents.ask_agent import answer_medicine_question

    try:
        answer = answer_medicine_question(
            sanitized_message,
            recommended_medicines,
            recommendation_client,
            medicine_list=medicine_list,
        )
        content = answer.get("answer") if isinstance(answer, dict) else str(answer)
        from datetime import datetime

        session.setdefault("messages", []).append({
            "type": "bot",
            "content": content,
            "ask": True,
            "timestamp": datetime.now().isoformat(),
        })
        _mark_session_modified(session)
        if sid:
            from src.services.session_manager import get_session_from_db, save_session_to_db

            sd = get_session_from_db(sid) or {}
            sd["messages"] = session.get("messages", []).copy()
            sd["last_activity"] = datetime.now()
            save_session_to_db(sid, sd)
        return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
    except Exception as e:
        logger.error("Ask route error: %s", e)
        return None


def _transition_counseling_to_physical(
    session: Any,
    triage_result: Optional[Dict[str, Any]],
    *,
    subcategory: str,
    symptom_text: str,
    reasoning: str,
) -> AskRouteState:
    counseling_mode_check = session.get("counseling_mode", {})
    if counseling_mode_check.get("active"):
        counseling_mode_check["active"] = False
        session["counseling_mode"] = counseling_mode_check
        _mark_session_modified(session)

    if triage_result:
        triage_result["category"] = "Physical"
        triage_result["subcategory"] = subcategory
        triage_result["reasoning"] = reasoning

    session.pop("should_handle_other_category", None)
    logger.info("✅ カテゴリをPhysicalに変更して薬推奨フローへ: %s", symptom_text)
    return AskRouteState(
        category="Physical",
        sanitized_message=symptom_text,
        user_message=symptom_text,
        is_question=False,
        triage_result=triage_result,
    )


def route_ask_category(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Optional[Dict[str, Any]],
    recommendation_client: OpenAI,
) -> AskRouteState:
    """
    Ask カテゴリの巨大分岐（不眠/眠気の薬推奨遷移・睡眠薬→カウンセリング）。
    早期 return 時は response を、Physical 継続時は category 等を返す。
    """
    counseling_mode_check = session.get("counseling_mode", {})
    is_insomnia_medicine_request = False
    is_sleepiness_medicine_request = False

    messages = session.get("messages", [])
    if messages:
        for msg in reversed(messages[-5:]):
            if msg.get("type") == "bot" and msg.get("counseling_medicine_info"):
                symptom_type_in_msg = counseling_mode_check.get("symptom_type", "")
                if symptom_type_in_msg == "insomnia" or "不眠" in msg.get("content", ""):
                    is_insomnia_medicine_request = True
                    logger.info("✅ 不眠カウンセリング関連の薬推奨リクエストを検出: %s", sanitized_message)
                    break
                if symptom_type_in_msg == "drowsiness" or "眠気" in msg.get("content", ""):
                    is_sleepiness_medicine_request = True
                    logger.info("✅ 眠気カウンセリング関連の薬推奨リクエストを検出: %s", sanitized_message)
                    break

    if (
        counseling_mode_check.get("active")
        and counseling_mode_check.get("symptom_type") == "insomnia"
    ) or is_insomnia_medicine_request:
        logger.info("✅ 不眠カウンセリング関連の薬推奨フローに移行: %s", sanitized_message)
        return _transition_counseling_to_physical(
            session,
            triage_result,
            subcategory="insomnia",
            symptom_text="一時的な不眠",
            reasoning="不眠カウンセリングから薬推奨への切り替え",
        )

    if (
        counseling_mode_check.get("active")
        and counseling_mode_check.get("symptom_type") == "drowsiness"
    ) or is_sleepiness_medicine_request:
        logger.info("✅ 眠気カウンセリング関連の薬推奨フローに移行: %s", sanitized_message)
        return _transition_counseling_to_physical(
            session,
            triage_result,
            subcategory="drowsiness",
            symptom_text="日中の眠気",
            reasoning="眠気カウンセリングから薬推奨への切り替え",
        )

    if any(kw in sanitized_message for kw in SLEEP_MEDICINE_KEYWORDS):
        from src.handlers.chat.chat_emotional_route import handle_emotional_category

        if triage_result:
            triage_result["category"] = "Emotional"
            triage_result["subcategory"] = "insomnia"
        emo_resp = handle_emotional_category(
            session,
            sid,
            user_message,
            sanitized_message,
            triage_result,
            recommendation_client,
            has_insomnia_keyword=True,
        )
        if emo_resp is not None:
            logger.info("✅ 睡眠薬質問から不眠カウンセリングフロー開始")
            return AskRouteState(response=emo_resp)

    return AskRouteState(
        category="Ask",
        sanitized_message=sanitized_message,
        user_message=user_message,
        triage_result=triage_result,
    )
