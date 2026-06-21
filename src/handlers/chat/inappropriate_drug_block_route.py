"""
違法薬物・規制薬物 — 即時ブロック応答（オーケストレーター / トリアージ follow-up 共通）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.session_manager import (
    append_user_message,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_BLOCK_TYPES = frozenset({"illegal", "controlled"})


def resolve_illegal_or_controlled_type(
    triage_result: Optional[dict],
    user_text: str,
) -> Optional[str]:
    """triage subcategory またはキーワード前置から illegal / controlled を判定。"""
    triage = triage_result or {}
    sub = (triage.get("subcategory") or "").lower()
    if "/illegal" in sub:
        return "illegal"
    if "/controlled" in sub:
        return "controlled"

    from src.services.counseling_triage import detect_inappropriate_request

    detected = detect_inappropriate_request(user_text or "", triage)
    if detected in _BLOCK_TYPES:
        return detected

    from src.services.llm_triage import detect_illegal_or_controlled_drug

    keyword_hit = detect_illegal_or_controlled_drug(user_text or "")
    if keyword_hit in _BLOCK_TYPES:
        return keyword_hit
    return None


def try_inappropriate_drug_block_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Optional[dict],
    *,
    append_user: bool = True,
) -> Optional[ResponseTuple]:
    """
    違法薬物・規制薬物リクエストに対し拒否メッセージを返す。
    """
    text = (sanitized_message or user_message or "").strip()
    request_type = resolve_illegal_or_controlled_type(triage_result, text)
    if request_type not in _BLOCK_TYPES:
        return None

    from src.services.counseling.counseling_templates import (
        generate_illegal_drug_rejection_message,
    )
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    block_message = generate_illegal_drug_rejection_message(request_type)
    title = "違法薬物のご相談" if request_type == "illegal" else "規制薬物のご相談"
    sage_diag = build_notice_status(
        block_message.strip(),
        title=title,
        variant="critical",
        kind=f"inappropriate_drug_{request_type}",
        show_feedback=True,
    ).to_client_dict()

    if append_user and user_message:
        append_user_message(session, user_message)

    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=block_message.strip(),
        inappropriate_request=True,
        request_type=request_type,
        illegal_drug_block=True,
    )
    session.setdefault("messages", []).append(bot_response)
    session.setdefault("inappropriate_requests", []).append(
        {
            "type": request_type,
            "timestamp": datetime.now().isoformat(),
            "user_message": text,
            "blocked": True,
        }
    )
    if hasattr(session, "modified"):
        session.modified = True

    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            if "messages" not in session_data:
                session_data["messages"] = []
            session_data["messages"].append(bot_response)
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)
        else:
            save_session_to_db(
                sid,
                {
                    "session_id": sid,
                    "username": session.get(
                        "username", f"ユーザー{get_next_user_number()}"
                    ),
                    "messages": list(session.get("messages", [])),
                    "session_active": True,
                    "last_activity": datetime.now(),
                    "client_ip": getattr(client_info, "client_ip", ""),
                    "user_agent": getattr(client_info, "user_agent", ""),
                    "user_attributes": session.get("user_attributes", {}),
                },
            )

    logger.warning(
        "🚫 違法/規制薬物を即時ブロック: type=%s session_id=%s",
        request_type,
        sid,
    )
    message_count = len(session.get("messages", []))
    return ({"status": "ok", "message_count": message_count}, 200)
