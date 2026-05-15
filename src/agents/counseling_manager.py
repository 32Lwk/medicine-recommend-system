"""
CounselingManager — Emotional カウンセリング開始（chat_emotional_route へ委譲）
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from openai import OpenAI


def start_counseling(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    client: OpenAI,
    *,
    symptom_type: Optional[str] = None,
    has_sleepiness_keyword: bool = False,
    has_insomnia_keyword: bool = False,
) -> Tuple[Optional[Tuple[dict, int]], Dict[str, Any]]:
    """CounselingManager → 完全版 emotional route"""
    from src.handlers.chat.chat_emotional_route import handle_emotional_category

    if symptom_type and triage_result is not None:
        triage_result = dict(triage_result)
        triage_result["subcategory"] = symptom_type

    resp = handle_emotional_category(
        session,
        sid,
        user_message,
        sanitized_message,
        triage_result,
        client,
        has_sleepiness_keyword=has_sleepiness_keyword,
        has_insomnia_keyword=has_insomnia_keyword,
    )
    if resp:
        if sid:
            session_data_flag = session.get("agent_handoff")
            if session_data_flag is None:
                session["agent_handoff"] = "CounselingManager"
        return resp, triage_result
    return None, triage_result
