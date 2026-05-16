"""
トリアージ confidence ゲート（ConfidenceGate への委譲）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def check_triage_confidence(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
    *,
    client_info: Any = None,
) -> Optional[ResponseTuple]:
    from src.services.confidence_gate import apply_confidence_gate

    early, updated = apply_confidence_gate(
        session,
        sid,
        user_message,
        sanitized_message,
        triage_result,
        recommendation_client,
        client_info=client_info,
    )
    if updated is not triage_result:
        session["_last_triage_result"] = updated
    return early
