"""Concierge 文脈 — dialogue_state 優先読取（Wave 2 / CCR 統合）。"""
from __future__ import annotations

from typing import Any


def resolve_last_intent_for_session(session: Any, sid: str | None = None) -> str | None:
    """
    直前 Concierge intent。
    v2 セッション: dialogue_state.concierge.last_intent → concierge_state フォールバック。
    """
    if session is None or not hasattr(session, "get"):
        return None

    from config.llm_flags import is_chat_pipeline_v2_for_session

    if is_chat_pipeline_v2_for_session(sid):
        from src.dialogue.context import load_dialogue_context

        ctx = load_dialogue_context(session)
        last = (ctx.get("concierge") or {}).get("last_intent")
        if last:
            return str(last)

    from src.agents.concierge_agent import get_concierge_state

    last = get_concierge_state(session).get("last_intent")
    return str(last) if last else None


def resolve_off_topic_turns(session: Any, sid: str | None = None) -> int:
    """雑談連続ターン数（redirect 昇格判定用）。"""
    if session is None or not hasattr(session, "get"):
        return 0

    from config.llm_flags import is_chat_pipeline_v2_for_session

    if is_chat_pipeline_v2_for_session(sid):
        from src.dialogue.context import load_dialogue_context

        ctx = load_dialogue_context(session)
        raw = (ctx.get("concierge") or {}).get("off_topic_turns")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass

    from src.agents.concierge_agent import get_concierge_state

    state = get_concierge_state(session)
    try:
        return int(state.get("off_topic_turns") or 0)
    except (TypeError, ValueError):
        return 0
