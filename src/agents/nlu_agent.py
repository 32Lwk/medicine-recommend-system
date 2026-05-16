"""
NLUAgent — hybrid_nlu_extraction のファサード（二重実装を避ける単一路）
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


def run_nlu_agent(
    user_text: str,
    user_info: Optional[Dict[str, Any]],
    client: Optional[OpenAI],
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    属性・症状 NLU。実体は hybrid_nlu_extraction に一本化。
    """
    user_info = dict(user_info or {})
    if client is None:
        return {"agent": "NLUAgent", "source": "no_client", "user_info": user_info}

    from src.core.rule_based_recommendation import hybrid_nlu_extraction

    try:
        nlu = hybrid_nlu_extraction(user_text, user_info, client, session_id)
        return {
            "agent": "NLUAgent",
            "source": "hybrid",
            "nlu": nlu,
            "user_info": user_info,
        }
    except Exception as e:
        logger.warning("NLUAgent hybrid failed: %s", e)
        return {"agent": "NLUAgent", "source": "error", "error": str(e), "user_info": user_info}


def run_triage_agent(
    user_text: str,
    client: OpenAI,
    *,
    user_info: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
    moderation_label: Optional[str] = None,
    attrs_changed: bool = False,
) -> Dict[str, Any]:
    pre = keyword_pre_triage(user_text)
    if pre:
        return pre

    from src.services.triage_cache import (
        build_cache_key,
        get_triage_cache,
        record_cache_event,
        should_skip_cache_lookup,
        should_skip_cache_write,
    )

    cache_key = build_cache_key(user_text, user_info)
    if use_cache:
        skip_lookup = should_skip_cache_lookup(
            text=user_text,
            moderation_label=moderation_label,
        )
        if skip_lookup:
            record_cache_event("skip_lookup", reason=skip_lookup)
        else:
            cached = get_triage_cache().get(cache_key)
            if cached:
                record_cache_event("hit")
                out = dict(cached)
                out["agent"] = "TriageAgent"
                out["cache_hit"] = True
                return out
            record_cache_event("miss")

    from src.services.llm_triage import llm_triage

    result = llm_triage(user_text, client, use_cache=False)
    result["agent"] = "TriageAgent"

    if use_cache:
        skip_write = should_skip_cache_write(
            text=user_text,
            result=result,
            moderation_label=moderation_label,
            attrs_changed=attrs_changed,
        )
        if skip_write:
            record_cache_event("skip_write", reason=skip_write)
        else:
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
