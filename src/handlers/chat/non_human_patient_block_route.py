"""ペット等への人間用市販薬相談 — 獣医師案内（オーケストレーター共通）。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.non_human_patient_guard import (
    build_non_human_patient_redirect_text,
    is_non_human_patient_query,
)
from src.services.session_manager import append_user_message

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def try_non_human_patient_redirect_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    *,
    append_user: bool = True,
) -> Optional[ResponseTuple]:
    text = (sanitized_message or user_message or "").strip()
    if not is_non_human_patient_query(text):
        return None

    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    body = build_non_human_patient_redirect_text()
    sage_diag = build_notice_status(
        body,
        title="ペットへの市販薬について",
        variant="caution",
        kind="non_human_patient_redirect",
        show_feedback=True,
    ).to_client_dict()

    if append_user and user_message:
        append_user_message(session, user_message)

    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=body,
    )
    session.setdefault("messages", []).append(bot_response)
    logger.info("non_human_patient_redirect: sid=%s", sid)
    return {"status": "ok", "message": body}, 200
