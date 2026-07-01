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
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    long_term_memory_block: str = "",
) -> Dict[str, Any]:
    from src.core.medicine.medicine_response_builder import chat_with_medicine_context

    result = chat_with_medicine_context(
        user_text,
        conversation_history if conversation_history is not None else recommended_medicines,
        medicine_list or recommended_medicines,
        client,
        session_id=session_id,
        long_term_memory_block=long_term_memory_block or None,
    )
    if isinstance(result, dict):
        result["agent"] = "AskAgent"
    return result
