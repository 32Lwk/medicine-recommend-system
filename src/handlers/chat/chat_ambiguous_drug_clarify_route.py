"""
品目未特定の飲み合わせ・併用質問 — Concierge Clarify テンプレート（LLM 雑談より優先）
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def ambiguous_drug_clarify_message(user_text: str) -> str:
    """品目未特定時の Clarify 本文（評価器 CLARIFY_HINTS と整合）。"""
    msg = (user_text or "").strip()
    if re.search(r"飲み合わせ|併用|一緒に", msg):
        return (
            "どのお薬同士の飲み合わせか教えていただけますか？"
            "お薬名が分かれば、こちらで一般的な情報をお伝えします。"
        )
    return "どのお薬についてのご質問か、製品名を教えていただけますか。"


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def try_ambiguous_drug_clarification(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    sanitized_message: str,
    user_message: str,
    *,
    route_source: str,
) -> Optional[ResponseTuple]:
    """QA gate が ambiguous_drug_clarify と判定したとき、テンプレ Clarify を返す。"""
    if route_source != "ambiguous_drug_clarify":
        return None

    from src.services.sage_bot_response import build_bot_response
    from src.services.session_manager import get_session_from_db, save_session_to_db
    from src.services.status_diagnosis_builder import build_concierge_text_status

    text = user_message or sanitized_message
    message = ambiguous_drug_clarify_message(text)
    sage_diag = build_concierge_text_status(
        message,
        title="確認",
        kind="concierge_clarify",
    ).to_client_dict()
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
    )
    session.setdefault("messages", []).append(bot_response)
    _mark_session_modified(session)

    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = session.get("messages", []).copy()
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)

    logger.info("💊 Ambiguous drug Clarify: session_id=%s text=%r", sid, text[:60])
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
