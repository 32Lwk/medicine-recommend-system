"""
推奨フロー用 NLU 解決（NLUAgent ファサードへ委譲）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def resolve_nlu_for_recommendation(
    user_text: str,
    user_info: Dict[str, Any],
    client: OpenAI,
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    from config.llm_flags import is_agent_enabled

    if is_agent_enabled():
        from src.agents.nlu_agent import run_nlu_agent
        from src.services.processing_status import mark_processing_step

        mark_processing_step(session_id, "attributes", detail_code="nlu")
        agent_out = run_nlu_agent(user_text, user_info, client, session_id=session_id)
        nlu = agent_out.get("nlu")
        if nlu:
            out = dict(nlu)
            out.setdefault("gender_detected", {"detected": False})
            out.setdefault("pregnancy_possible", {"detected": False})
            out["_nlu_agent"] = agent_out.get("source", "hybrid")
            return out

    from src.core.rule_based_recommendation import hybrid_nlu_extraction

    return hybrid_nlu_extraction(user_text, user_info, client, session_id)
