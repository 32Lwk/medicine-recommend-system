"""IntentRouter shadow 観測ログ（Wave 1b）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def log_dialogue_route_shadow(
    *,
    session_id: Optional[str],
    user_input: str,
    decision: dict[str, Any],
    triage_category: Optional[str] = None,
    triage_subcategory: Optional[str] = None,
    mismatch: bool = False,
    dialogue_flags: Optional[dict[str, bool]] = None,
) -> None:
    """dialogue_route_shadow を app.log + JSONL に記録。"""
    try:
        from src.utils.structured_logger import emit_dialogue_route_shadow
    except ImportError:
        logger.debug("emit_dialogue_route_shadow unavailable")
        return

    emit_dialogue_route_shadow(
        session_id=session_id or "",
        user_input=user_input,
        decision=decision,
        triage_category=triage_category,
        triage_subcategory=triage_subcategory,
        mismatch=mismatch,
        dialogue_flags=dialogue_flags,
    )
