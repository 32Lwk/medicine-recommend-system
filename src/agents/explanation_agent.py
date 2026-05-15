"""
ExplanationAgent — rule_based 推奨結果を固定入力として説明生成
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def generate_explanations_for_recommendation(
    recommended_medicines: List[Dict[str, Any]],
    nlu_result: Dict[str, Any],
    user_info: Dict[str, Any],
    client: OpenAI,
    *,
    safety_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    推奨医薬品リスト（rule_based 出力）を変更せず、説明のみ生成する。
    """
    from src.core.explanation_generator import (
        generate_explanation,
        generate_usage_notes_and_consultation_with_gpt,
    )

    safety_result = safety_result or {}
    notes_bundle = generate_usage_notes_and_consultation_with_gpt(
        recommended_medicines, nlu_result, user_info, client
    )
    explanations: List[str] = []
    for med in recommended_medicines[:3]:
        try:
            explanations.append(
                generate_explanation(med, nlu_result, safety_result, user_info)
            )
        except Exception as e:
            logger.warning("ExplanationAgent per-medicine skip: %s", e)

    return {
        "agent": "ExplanationAgent",
        "usage_notes_bundle": notes_bundle,
        "explanations": explanations,
        "medicine_names": [
            m.get("product_name") or m.get("name") or "" for m in recommended_medicines[:3]
        ],
    }
