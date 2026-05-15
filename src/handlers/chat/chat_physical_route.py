"""
Physical カテゴリ — rule_based プレビュー・カウンセリングからの薬推奨遷移
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

MENSTRUAL_KEYWORDS = [
    "生理不順", "月経不順", "生理が遅れ", "生理が来ない", "生理周期",
    "月経異常", "血の道症", "生理痛", "月経痛", "生理の遅れ",
]


@dataclass
class PhysicalRouteState:
    """Physical 分岐後のメッセージ・カテゴリ状態"""

    category: str
    sanitized_message: str
    user_message: str
    is_question: Optional[bool] = None


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def apply_menstrual_physical_override(category: str, sanitized_message: str) -> str:
    """月経不順関連は Emotional でも Physical 推奨へ"""
    if category == "Emotional" and any(kw in sanitized_message for kw in MENSTRUAL_KEYWORDS):
        logger.info("🔄 月経不順関連症状検出により、カテゴリをEmotionalからPhysicalに変更")
        return "Physical"
    return category


def prepare_physical_recommendation(
    session: Any,
    sanitized_message: str,
    client: OpenAI,
    sid: Optional[str] = None,
) -> Dict[str, Any]:
    """PhysicalOrchestrator 経由で rule_based 結果をセッションに記録"""
    from src.agents.physical_orchestrator import run_physical_recommendation

    user_info = session.get("user_attributes") or {}
    result = run_physical_recommendation(
        sanitized_message,
        user_info=user_info,
        client=client,
        session_id=sid,
    )
    session["agent_rule_based_preview"] = {
        "names": result.get("recommended_medicine_names", []),
        "algorithm": result.get("algorithm", "rule_based"),
    }
    _mark_session_modified(session)
    return result


def prepare_physical_category(
    session: Any,
    sanitized_message: str,
    user_message: str,
    category: str,
    recommendation_client: OpenAI,
    sid: Optional[str],
    *,
    is_question: Optional[bool] = None,
) -> PhysicalRouteState:
    """
    Physical カテゴリ前処理（エージェント preview・不眠/眠気カウンセリングからの遷移）。
    後続の推奨フローへ fall-through するため状態のみ返す。
    """
    try:
        from config.llm_flags import is_agent_enabled, is_agent_session_eligible

        if is_agent_enabled() and is_agent_session_eligible(sid):
            prepare_physical_recommendation(
                session, sanitized_message, recommendation_client, sid
            )
    except Exception as phys_agent_err:
        logger.debug("Physical orchestrator preview skipped: %s", phys_agent_err)

    if session.get("insomnia_medicine_recommendation"):
        user_text = session.pop("insomnia_user_text", "一時的な不眠")
        session.pop("insomnia_medicine_recommendation", None)
        _mark_session_modified(session)
        logger.info("✅ 不眠の薬推奨フローに移行: %s", user_text)
        return PhysicalRouteState(
            category=category,
            sanitized_message=user_text,
            user_message=user_text,
            is_question=False,
        )

    if session.get("sleepiness_medicine_recommendation"):
        user_text = session.pop("sleepiness_user_text", "日中の眠気")
        session.pop("sleepiness_medicine_recommendation", None)
        _mark_session_modified(session)
        logger.info("✅ 眠気の薬推奨フローに移行: %s", user_text)
        return PhysicalRouteState(
            category=category,
            sanitized_message=user_text,
            user_message=user_text,
            is_question=False,
        )

    return PhysicalRouteState(
        category=category,
        sanitized_message=sanitized_message,
        user_message=user_message,
        is_question=is_question,
    )
