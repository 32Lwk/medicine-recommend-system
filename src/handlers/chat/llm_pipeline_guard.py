"""
confidence_gate_done 直後の LLM インフラ / clarification ループ短絡（単一入口）。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_CLARIFICATION_LOOP_THRESHOLD = 2
_CLARIFICATION_PATTERNS = (
    re.compile(r"確信度が低いため確認"),
    re.compile(r"もう少し詳しく教えて"),
    re.compile(r"具体的に教えていただけますか"),
)


def _normalize_clarification_key(text: str) -> str:
    return " ".join((text or "").split())[:500]


def record_clarification_text(session: Any, clarification_text: str) -> int:
    """同一 clarification 文案の出現回数を記録し、更新後のカウントを返す。"""
    key = _normalize_clarification_key(clarification_text)
    if not key:
        return 0
    counts = session.setdefault("clarification_text_counts", {})
    if not isinstance(counts, dict):
        counts = {}
        session["clarification_text_counts"] = counts
    counts[key] = int(counts.get(key, 0)) + 1
    return int(counts[key])


def clarification_loop_exceeded(session: Any, clarification_text: str) -> bool:
    counts = session.get("clarification_text_counts") or {}
    key = _normalize_clarification_key(clarification_text)
    return bool(key) and int(counts.get(key, 0)) >= _CLARIFICATION_LOOP_THRESHOLD


def _last_bot_clarification_text(session: Any) -> str:
    messages = session.get("messages") or []
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        content = str(msg.get("content") or msg.get("personalized_advice") or "").strip()
        if not content:
            diag = msg.get("diagnosis") or {}
            content = str(diag.get("message") or diag.get("title") or "").strip()
        if content and any(p.search(content) for p in _CLARIFICATION_PATTERNS):
            return content
    return ""


def try_llm_pipeline_short_circuit(
    session: Any,
    sid: Optional[str],
    triage_result: Optional[dict],
    *,
    user_message: str = "",
) -> Optional[ResponseTuple]:
    """
    LLM インフラ障害または clarification ループ時に早期 200 を返す。
    通常フロー継続時は None。
    """
    from src.services.llm_unavailability import (
        build_llm_unavailable_bot_message,
        is_llm_triage_infrastructure_error,
        mark_llm_infrastructure_degraded,
        should_block_llm_dependent_reply,
    )

    if should_block_llm_dependent_reply(session):
        logger.info("LLM pipeline short-circuit: session already degraded sid=%s", sid)
        return {"status": "ok", "message_count": len(session.get("messages", []))}, 200

    if is_llm_triage_infrastructure_error(triage_result):
        mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
        bot = build_llm_unavailable_bot_message(session, sid)
        session.setdefault("messages", []).append(bot)
        return {"status": "ok", "message_count": len(session.get("messages", []))}, 200

    last_clarify = _last_bot_clarification_text(session)
    if last_clarify and clarification_loop_exceeded(session, last_clarify):
        logger.warning(
            "Clarification loop detected sid=%s count>=%s",
            sid,
            _CLARIFICATION_LOOP_THRESHOLD,
        )
        mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
        bot = build_llm_unavailable_bot_message(session, sid)
        session.setdefault("messages", []).append(bot)
        return {"status": "ok", "message_count": len(session.get("messages", []))}, 200

    return None
