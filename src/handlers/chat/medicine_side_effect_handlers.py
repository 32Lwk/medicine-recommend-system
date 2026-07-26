"""推奨履歴なしの医薬品副作用 Q&A ハンドラ（CSV 第一 → KB 補完）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.services.medicine_side_effect_routing import (
    mentions_drowsiness_side_effect,
    resolve_side_effect_query_subject,
)
from src.services.medicine_side_effect_section import (
    build_side_effect_section,
    find_products_for_side_effect,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _try_kb_fallback(
    user_message: str,
    product_name: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> Optional[str]:
    try:
        from config.llm_flags import is_medicine_side_effect_kb_enabled

        if not is_medicine_side_effect_kb_enabled():
            return None
    except ImportError:
        return None

    try:
        from src.services.bedrock_kb_retrieve import retrieve_medicine_context

        query = f"{product_name} 副作用 {user_message}"
        kb = retrieve_medicine_context(
            query,
            recommended_medicines=recommended_medicines
            or [{"product_name": product_name}],
            conversation_history=conversation_history,
        )
        chunks = kb.get("chunks") or []
        if not chunks:
            return None
        snippet = str(chunks[0])[:800].strip()
        uris = kb.get("source_uris") or []
        citation = uris[0] if uris else "Knowledge Base"
        return (
            f"「{product_name}」の副作用について（KB 参照）:\n{snippet}\n\n"
            f"出典: {citation}\n\n"
            "個人差があります。気になる症状が続く場合は使用を中止し、"
            "薬剤師・医師にご相談ください。"
        )
    except Exception:
        logger.debug("KB fallback failed", exc_info=True)
        return None


def handle_medicine_side_effect_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
) -> ResponseTuple:
    """副作用 Q&A — 単独副作用のみ（複合 intent は medicine_qa へ委譲）。"""
    from src.handlers.chat.chat_medicine_qa_html import finalize_medicine_qa_response
    from src.services.medicine_qa_routing import (
        infer_medicine_qa_focuses,
        should_use_medicine_qa_unified,
    )
    from src.services.session_manager import get_session_from_db

    session_data = get_session_from_db(sid) if sid else {}
    conversation_history = session_data.get("messages", [])[-10:]
    user_attributes = session_data.get("user_attributes") or session.get("user_attributes") or {}

    focuses = infer_medicine_qa_focuses(
        user_message,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
    )
    if should_use_medicine_qa_unified(focuses, user_message=user_message):
        from src.handlers.chat.medicine_context_handlers import handle_medicine_information_qa

        return handle_medicine_information_qa(session, client_info, sid, user_message)

    subject = resolve_side_effect_query_subject(user_message) or user_message
    products = find_products_for_side_effect(subject)
    product_name = (
        str(products[0].get("product_name") or subject)
        if products
        else subject
    )

    chat_response = build_side_effect_section(
        user_message,
        products,
        product_name=product_name,
    )
    chat_response.update(
        {
            "medicine_details": "",
            "interactions": "",
            "doping_check": "",
            "consultation_advice": "",
            "qa_kind": "medicine_side_effect_qa",
            "source": "medicine_side_effects.csv",
        }
    )

    if not chat_response.get("side_rows"):
        kb_answer = _try_kb_fallback(
            user_message,
            product_name,
            conversation_history=conversation_history,
            recommended_medicines=products,
        )
        if kb_answer:
            chat_response["answer"] = kb_answer
            chat_response["source"] = "bedrock_kb"
    chat_response.pop("side_rows", None)

    msg_count = finalize_medicine_qa_response(
        session,
        client_info,
        sid,
        user_message,
        chat_response,
    )
    if sid and session is not None:
        session.setdefault("messages", [])
        if session["messages"]:
            last = session["messages"][-1]
            if isinstance(last, dict):
                diag = last.setdefault("diagnosis", {})
                if isinstance(diag, dict):
                    diag["kind"] = "medicine_side_effect_qa"
                    diag["render"] = "sage_qa"

    return {"status": "ok", "message_count": msg_count}, 200
