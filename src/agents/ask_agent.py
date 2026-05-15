"""
AskAgent — 推奨後の医薬品 Q&A（chat_with_medicine_context ラッパ）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI


def answer_medicine_question(
    user_text: str,
    recommended_medicines: List[Dict[str, Any]],
    client: OpenAI,
    *,
    medicine_list: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from src.core.medicine.medicine_response_builder import chat_with_medicine_context

    result = chat_with_medicine_context(
        user_text,
        recommended_medicines,
        medicine_list or [],
        client,
    )
    if isinstance(result, dict):
        result["agent"] = "AskAgent"
    return result
