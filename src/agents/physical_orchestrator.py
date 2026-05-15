"""
PhysicalOrchestrator — 決定的フロー + rule_based 関数ツール（唯一のランキング）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from src.agents.tools.recommendation_tool import invoke_rule_based_recommendation

logger = logging.getLogger(__name__)


def run_physical_recommendation(
    user_text: str,
    user_info: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAI] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    rule_based_medicine_recommendation を1回呼び、メタデータを付与して返す。
    """
    result = invoke_rule_based_recommendation(
        user_text,
        user_info=user_info or {},
        client=client,
        session_id=session_id,
    )
    result["orchestrator"] = "PhysicalOrchestrator"
    meds = result.get("recommended_medicines") or []
    logger.info(
        "PhysicalOrchestrator: %d medicines via rule_based",
        len(meds),
    )
    return result
