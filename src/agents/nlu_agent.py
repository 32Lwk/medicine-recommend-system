"""
NLUAgent — 軽量ルールで属性充足を確認し、不足時のみ LLM NLU
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def _rule_sufficient(user_info: Dict[str, Any], user_text: str) -> bool:
    if not user_text or len(user_text.strip()) < 4:
        return False
    attrs = user_info or {}
    has_age = bool(attrs.get("age"))
    has_gender = bool(attrs.get("gender"))
    has_symptoms = bool(attrs.get("symptoms")) or len(user_text.strip()) >= 8
    return has_age and has_gender and has_symptoms


def run_nlu_agent(
    user_text: str,
    user_info: Optional[Dict[str, Any]],
    client: Optional[OpenAI],
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    user_info = dict(user_info or {})
    if _rule_sufficient(user_info, user_text):
        return {
            "agent": "NLUAgent",
            "source": "rule",
            "skipped_llm": True,
            "user_info": user_info,
        }

    if client is None:
        return {"agent": "NLUAgent", "source": "rule", "user_info": user_info}

    try:
        from src.core.nlu_service import hybrid_nlu_extraction

        nlu = hybrid_nlu_extraction(user_text, user_info, client, session_id=session_id)
        return {"agent": "NLUAgent", "source": "llm", "nlu": nlu, "user_info": user_info}
    except Exception as e:
        logger.warning("NLUAgent LLM fallback failed: %s", e)
        return {"agent": "NLUAgent", "source": "error", "error": str(e), "user_info": user_info}
