"""Concierge 実行 intent と triage / diagnosis / analytics メタデータの同期。"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def sync_concierge_execution_metadata(
    session: Any,
    *,
    sid: Optional[str],
    resolved_intent: str,
    triage_result: Optional[dict[str, Any]],
    user_text: str,
    response_preview: str = "",
) -> None:
    """dispatch 決定と実行 intent の analytics 乖離を防ぐ。"""
    if triage_result is not None:
        triage_result["concierge_intent"] = resolved_intent
        triage_result["concierge_intent_source"] = "execution_sync"
        session["last_triage_result"] = triage_result

    session["last_concierge_intent"] = resolved_intent

    messages = session.get("messages") or []
    if not messages:
        return

    last = messages[-1]
    if not isinstance(last, dict) or last.get("type") != "bot":
        return

    last["concierge_intent"] = resolved_intent
    expected_kind = f"concierge_{resolved_intent}"

    diagnosis = last.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis["kind"] = expected_kind
        fb = diagnosis.get("feedback_context")
        if isinstance(fb, dict):
            fb["concierge_intent"] = resolved_intent
            fb["ai_response"] = f"concierge:{resolved_intent}"
            if response_preview:
                fb.setdefault("response_preview", response_preview[:500])
        else:
            diagnosis["feedback_context"] = {
                "user_message": user_text,
                "ai_response": f"concierge:{resolved_intent}",
                "concierge_intent": resolved_intent,
            }

    try:
        from src.utils.structured_logger import emit_dialogue_route_execution

        shadow = session.get("_intent_router_shadow") or {}
        dispatch_sub = shadow.get("sub_route") if isinstance(shadow, dict) else None
        mismatch = bool(dispatch_sub and dispatch_sub != resolved_intent)
        emit_dialogue_route_execution(
            session_id=sid or "",
            user_input=user_text,
            dispatch_sub_route=dispatch_sub,
            resolved_concierge_intent=resolved_intent,
            resolved_execution_intent=resolved_intent,
            mismatch=mismatch,
            handler="concierge_agent",
            extra={"sync": "concierge_execution_metadata"},
        )
    except Exception:
        logger.debug("concierge execution sync log skipped", exc_info=True)
