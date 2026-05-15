"""
rule_based_medicine_recommendation の関数ツールラッパ（推奨の唯一の真実源）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI


def invoke_rule_based_recommendation(
    user_text: str,
    user_info: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAI] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    from src.core.rule_based_recommendation import rule_based_medicine_recommendation

    result = rule_based_medicine_recommendation(
        user_text,
        user_info or {},
        client,
        session_id=session_id,
    )
    meds = result.get("recommended_medicines") or []
    result["recommended_medicine_names"] = [
        m.get("product_name") or m.get("name") or "" for m in meds[:3]
    ]
    result["algorithm"] = "rule_based"
    return result


def as_tool_schema() -> Dict[str, Any]:
    return {
        "name": "rule_based_medicine_recommendation",
        "description": (
            "OTC推奨上位3件をルールベーススコアで返す。LLMはランキングを変更しない。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_text": {"type": "string"},
                "user_info": {"type": "object"},
            },
            "required": ["user_text"],
        },
    }
