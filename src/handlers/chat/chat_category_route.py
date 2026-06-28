"""
トリアージ後のカテゴリ別ルーティング（Emotional / Physical / Ask）
"""
from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.handlers.chat.chat_ask_route import route_ask_category
from src.handlers.chat.chat_emotional_route import handle_emotional_category
from src.handlers.chat.chat_physical_route import (
    apply_physical_category_overrides,
    prepare_physical_category,
)
from src.services.confidence_policy import should_defer_category_routing
from src.services.session_manager import save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


@dataclass
class CategoryRouteResult:
    """カテゴリルート結果"""

    response: Optional[ResponseTuple] = None
    category: str = "Other"
    sanitized_message: str = ""
    user_message: str = ""
    is_question: Optional[bool] = None
    triage_result: Optional[Dict[str, Any]] = field(default_factory=dict)


def route_triage_category(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
    *,
    inappropriate_request_detected: bool,
    has_sleepiness_keyword: bool = False,
    has_insomnia_keyword: bool = False,
    is_question: Optional[bool] = None,
) -> CategoryRouteResult:
    """
    ステップ4: カテゴリ別分岐（不適切要求・Emotional・Physical・Ask）。
    """
    category = triage_result.get("category", "Other")
    subcategory = (triage_result.get("subcategory") or "").lower()
    confidence = float(triage_result.get("confidence", 1.0))

    if category == "Emergency":
        from src.handlers.chat.emergency_dispatch import dispatch_emergency

        emerg = dispatch_emergency(
            session,
            recommendation_client,
            sid,
            sanitized_message,
            recommendation_client,
            triage_result,
        )
        if emerg is not None:
            return CategoryRouteResult(response=emerg)

    if category == "Other" and "inappropriate_request" in subcategory and not inappropriate_request_detected:
        early = _handle_inappropriate_from_triage(
            session,
            sid,
            user_message,
            sanitized_message,
            triage_result,
            recommendation_client,
            category=category,
            confidence=confidence,
        )
        if early is not None:
            return CategoryRouteResult(response=early)

    if should_defer_category_routing(category, confidence, session):
        return CategoryRouteResult(
            category=category,
            sanitized_message=sanitized_message,
            user_message=user_message,
            is_question=is_question,
            triage_result=triage_result,
        )

    category = apply_physical_category_overrides(category, sanitized_message)

    if category == "Emotional":
        emo_resp = handle_emotional_category(
            session,
            sid,
            user_message,
            sanitized_message,
            triage_result,
            recommendation_client,
            has_sleepiness_keyword=has_sleepiness_keyword,
            has_insomnia_keyword=has_insomnia_keyword,
        )
        if emo_resp is not None:
            return CategoryRouteResult(response=emo_resp)

    elif category == "Physical":
        phys = prepare_physical_category(
            session,
            sanitized_message,
            user_message,
            category,
            recommendation_client,
            sid,
            is_question=is_question,
        )
        return CategoryRouteResult(
            category=phys.category,
            sanitized_message=phys.sanitized_message,
            user_message=phys.user_message,
            is_question=phys.is_question,
            triage_result=triage_result,
        )

    elif category == "Ask":
        ask = route_ask_category(
            session,
            sid,
            user_message,
            sanitized_message,
            triage_result,
            recommendation_client,
        )
        if ask.response is not None:
            return CategoryRouteResult(response=ask.response)
        return CategoryRouteResult(
            category=ask.category,
            sanitized_message=ask.sanitized_message,
            user_message=ask.user_message,
            is_question=ask.is_question,
            triage_result=ask.triage_result or triage_result,
        )

    return CategoryRouteResult(
        category=category,
        sanitized_message=sanitized_message,
        user_message=user_message,
        is_question=is_question,
        triage_result=triage_result,
    )


def _handle_inappropriate_from_triage(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
    *,
    category: str,
    confidence: float,
) -> Optional[ResponseTuple]:
    try:
        from src.services.counseling_response import (
            detect_inappropriate_request,
            generate_counseling_response,
            generate_follow_up_questions,
            log_counseling_response,
            start_counseling_mode,
        )

        from src.handlers.chat.controlled_drug_routing import (
            mark_controlled_drug_counseling_done,
            resolve_inappropriate_counseling_flags,
        )

        request_type = detect_inappropriate_request(sanitized_message, triage_result)
        if not request_type:
            return None

        start_counseling, counseling_response, symptom_type = resolve_inappropriate_counseling_flags(
            session,
            request_type,
        )
        from src.dialogue.history import resolve_counseling_history_with_fallback

        conversation_history = resolve_counseling_history_with_fallback(session, sid)
        initial_response = generate_counseling_response(
            symptom_type,
            user_message,
            recommendation_client,
            conversation_history=conversation_history,
            session_id=sid,
        )
        initial_questions = (
            generate_follow_up_questions(symptom_type, {}, recommendation_client)
            if start_counseling
            else []
        )

        if start_counseling:
            start_counseling_mode(session, symptom_type, initial_questions)
            try:
                from src.dialogue.sync_legacy import mirror_counseling_mode

                mirror_counseling_mode(session, sid)
            except Exception:
                pass
        if request_type == "controlled" and counseling_response:
            mark_controlled_drug_counseling_done(session)

        session.setdefault("inappropriate_requests", []).append({
            "type": request_type,
            "timestamp": datetime.now().isoformat(),
            "user_message": sanitized_message,
        })

        from src.services.sage_bot_response import build_counseling_bot

        session.setdefault("messages", []).append(
            build_counseling_bot(
                session,
                sid,
                initial_response,
                title="カウンセリング",
                kind=f"counseling_inappropriate_{request_type}",
                counseling=counseling_response,
                inappropriate_request=True,
                request_type=request_type,
            )
        )

        log_counseling_response(
            session_id=sid,
            response_content=initial_response,
            response_type="counseling_inappropriate_request",
            category=category,
            confidence=confidence,
            counseling_mode=session.get("counseling_mode"),
            user_input=user_message,
            conversation_history=conversation_history,
        )

        logger.warning("⚠️ 不適切な要求検出: type=%s, session_id=%s", request_type, sid)
        if hasattr(session, "modified"):
            session.modified = True
        save_session_to_db(sid, session)
        return ({
            "response": initial_response,
            "questions": initial_questions,
            "counseling": counseling_response,
            "inappropriate_request": True,
        }, 200)
    except Exception as e:
        logger.error("❌ 不適切な要求処理エラー: %s", e)
        traceback.print_exc()
        return None
