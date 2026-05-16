"""
TriageAgent — LLMトリアージのエージェントラッパ（医薬品は選ばない）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from src.agents.protocols import (
    HandoffResult,
    emotional_handoff,
    emergency_handoff,
    physical_handoff,
)

logger = logging.getLogger(__name__)

_EMERGENCY_KEYWORDS = (
    "胸が痛", "息ができない", "呼吸困難", "大量出血", "意識がもうろう",
    "119", "救急", "死にそう", "自殺",
)


def keyword_pre_triage(user_text: str) -> Optional[Dict[str, Any]]:
    """決定的キーワード前置（LLM 前の安全ネット）"""
    t = (user_text or "").strip()
    if not t:
        return None
    for kw in _EMERGENCY_KEYWORDS:
        if kw in t:
            return {
                "category": "Emergency",
                "subcategory": "keyword_match",
                "confidence": 0.95,
                "requires_immediate_action": True,
                "reasoning": f"緊急キーワード検出: {kw}",
                "agent": "TriageAgent",
                "pre_triage": True,
            }
    return None


_CATEGORY_HANDOFF = {
    "Physical": physical_handoff,
    "Emotional": emotional_handoff,
    "Emergency": emergency_handoff,
    "Ask": "AskHandler",
    "Other": "OtherHandler",
}


def run_triage_agent(
    user_text: str,
    client: OpenAI,
    *,
    user_info: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    pre = keyword_pre_triage(user_text)
    if pre:
        try:
            from src.services.routing_validator import verify_routing_async

            verify_routing_async(
                route_kind="emergency_keyword",
                user_text=user_text,
                decided_category="Emergency",
                client=client,
                extra={"pre_triage": True},
            )
        except Exception:
            pass
        return pre

    from src.services.triage_cache import build_cache_key, get_triage_cache
    from src.services.triage_history import history_digest

    hist_d = history_digest(conversation_history or [])
    cache_key = build_cache_key(user_text, user_info, history_digest=hist_d)
    if use_cache:
        cached = get_triage_cache().get(cache_key)
        if cached:
            out = dict(cached)
            out["agent"] = "TriageAgent"
            out["cache_hit"] = True
            return out

    from src.services.llm_triage import llm_triage

    result = llm_triage(
        user_text,
        client,
        use_cache=use_cache,
        conversation_history=conversation_history,
    )
    result["agent"] = "TriageAgent"
    if use_cache:
        get_triage_cache().set(cache_key, result)
    return result


def resolve_handoff(
    triage_result: Dict[str, Any],
    user_text: str,
    user_info: Optional[Dict[str, Any]] = None,
) -> HandoffResult:
    category = (triage_result or {}).get("category") or "Other"
    subcategory = (triage_result or {}).get("subcategory") or ""
    confidence = float((triage_result or {}).get("confidence") or 0)

    if category == "Emergency" or triage_result.get("requires_immediate_action"):
        return emergency_handoff(triage_result.get("reasoning") or "triage_emergency")

    factory = _CATEGORY_HANDOFF.get(category)
    if factory is physical_handoff:
        return physical_handoff(user_text, user_info or {})
    if factory is emotional_handoff:
        return emotional_handoff(subcategory or "general")
    if isinstance(factory, str):
        return HandoffResult(factory, {"category": category, "confidence": confidence})

    return HandoffResult("OtherHandler", {"category": category, "confidence": confidence})
