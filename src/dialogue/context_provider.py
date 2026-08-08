"""ContextProvider — agent_kind 別履歴窓（Wave 1a）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.services.triage_history import get_recent_messages, history_digest

AGENT_KIND_LIMITS: dict[str, int] = {
    "default": 8,
    "session_ops": 6,
    "physical": 12,
    "counseling": 10,
    "concierge": 8,
    "emergency": 4,
    "store": 6,
    "emotional": 10,
}


@dataclass(frozen=True)
class ContextBundle:
    agent_kind: str
    messages: list[dict[str, Any]]
    history_digest: str
    memory_block: str
    max_turns: int


def resolve_history_limit(agent_kind: str) -> int:
    return AGENT_KIND_LIMITS.get(agent_kind, AGENT_KIND_LIMITS["default"])


def build_context_bundle(
    session: Any,
    sid: str | None,
    agent_kind: str = "default",
) -> ContextBundle:
    """agent_kind に応じた履歴窓と長期記憶ブロックを組み立てる。"""
    limit = resolve_history_limit(agent_kind)
    messages = get_recent_messages(session, sid, limit=limit)
    memory_block = ""
    if agent_kind in ("default", "physical", "counseling", "concierge", "session_ops"):
        from src.services.line_user_memory import is_line_memory_session

        if is_line_memory_session(sid, session):
            from src.services.line_memory_context import get_llm_conversation_context

            mem_messages, memory_block = get_llm_conversation_context(
                session, sid, limit=limit
            )
            if mem_messages:
                messages = mem_messages
        else:
            from src.services.medicine_thread_context import expand_messages_for_llm

            messages = expand_messages_for_llm(messages, max_turns=limit)

    digest = history_digest(messages)

    return ContextBundle(
        agent_kind=agent_kind,
        messages=messages,
        history_digest=digest,
        memory_block=memory_block or "",
        max_turns=limit,
    )
