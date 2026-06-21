"""
「心が痛い」等 — 身体的心臓症状 vs 心理的症状の確認カード
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def is_ambiguous_heart_triage(triage_result: dict | None) -> bool:
    if not triage_result:
        return False
    sub = (triage_result.get("subcategory") or "").lower()
    return "ambiguous_heart" in sub


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def try_ambiguous_heart_clarification(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    sanitized_message: str,
    user_message: str,
    triage_result: dict,
) -> Optional[ResponseTuple]:
    """Ambiguous_Heart 初回のみ、心臓の身体的症状か心理的症状か確認する。"""
    if not is_ambiguous_heart_triage(triage_result):
        return None
    if session.get("ambiguous_heart_clarify_sent"):
        return None

    from src.services.sage_bot_response import build_bot_response
    from src.services.session_manager import get_session_from_db, save_session_to_db
    from src.services.status_diagnosis_builder import build_ambiguous_heart_clarification_status

    message = (
        "「心が痛い」とのことですね。状況によって対応が大きく異なります。"
        "胸や心臓の物理的な痛み（動悸・圧迫感・息苦しさなど）ですか？"
        "それとも、心のつらさや悲しみなど、気持ちの痛みに近い感覚でしょうか？"
        "該当する方を選ぶか、具体的な症状を教えてください。"
    )
    feedback_ctx = {
        "user_message": user_message or sanitized_message,
        "ai_response": message,
    }
    sage_diag = build_ambiguous_heart_clarification_status(
        message,
        feedback_context=feedback_ctx,
    ).to_client_dict()
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
        requires_confirmation=True,
        ambiguous_heart_clarification=True,
        triage_result=triage_result,
    )
    session.setdefault("messages", []).append(bot_response)
    session["ambiguous_heart_clarify_sent"] = True
    _mark_session_modified(session)

    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = session.get("messages", []).copy()
            session_data["ambiguous_heart_clarify_sent"] = True
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)

    logger.info("❤️ Ambiguous_Heart 確認カードを返却: session_id=%s", sid)
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
