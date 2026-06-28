"""DialogueContext — load/save 合成ビューと dual-write（Wave 1a）。"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

DIALOGUE_STATE_KEY = "dialogue_state"


def empty_dialogue_state() -> dict[str, Any]:
    return {
        "version": 1,
        "pending": {},
        "concierge": {},
        "counseling": {},
        "handoff": {},
        "flags": {},
    }


def load_dialogue_context(session: Any) -> dict[str, Any]:
    """
    合成ビューを返す。
    優先: dialogue_state > concierge_state / pending_memory_delete 等レガシー。
    """
    if session is None or not hasattr(session, "get"):
        return empty_dialogue_state()

    raw = session.get(DIALOGUE_STATE_KEY)
    ctx = copy.deepcopy(raw if isinstance(raw, dict) else empty_dialogue_state())
    ctx.setdefault("version", 1)
    ctx.setdefault("pending", {})
    ctx.setdefault("concierge", {})
    ctx.setdefault("counseling", {})
    ctx.setdefault("handoff", {})
    ctx.setdefault("flags", {})

    legacy_pending = session.get("pending_memory_delete")
    if isinstance(legacy_pending, dict) and not ctx["pending"].get("session_delete"):
        ctx["pending"]["session_delete"] = {
            "scope": legacy_pending.get("scope") or "all",
            "requested_at": legacy_pending.get("requested_at")
            or datetime.now(timezone.utc).isoformat(),
        }

    concierge_state = session.get("concierge_state")
    if isinstance(concierge_state, dict):
        conc = ctx["concierge"]
        if concierge_state.get("last_intent") and not conc.get("last_intent"):
            conc["last_intent"] = concierge_state.get("last_intent")
        if concierge_state.get("topic") and not conc.get("topic"):
            conc["topic"] = concierge_state.get("topic")
        if conc.get("off_topic_turns") is None and concierge_state.get("off_topic_turns") is not None:
            try:
                conc["off_topic_turns"] = int(concierge_state.get("off_topic_turns") or 0)
            except (TypeError, ValueError):
                conc["off_topic_turns"] = 0

    if session.get("counseling_mode") and not ctx["counseling"].get("active"):
        ctx["counseling"]["active"] = True

    counseling_mode = session.get("counseling_mode")
    if isinstance(counseling_mode, dict):
        c = ctx["counseling"]
        if counseling_mode.get("symptom_type") and not c.get("theme"):
            c["theme"] = counseling_mode.get("symptom_type")
        if counseling_mode.get("active") is True:
            c["active"] = True

    handoff_target = session.get("agent_handoff")
    if handoff_target and not (ctx.get("handoff") or {}).get("target"):
        ctx.setdefault("handoff", {})["target"] = str(handoff_target)

    if session.get("_fever_context_active"):
        ctx["flags"]["fever_context"] = True

    episode_id = session.get("episode_id")
    if episode_id and not ctx.get("episode_id"):
        ctx["episode_id"] = episode_id

    routing = ctx.get("routing")
    if not isinstance(routing, dict) or not routing.get("primary_route"):
        shadow = session.get("_intent_router_shadow")
        if isinstance(shadow, dict) and shadow.get("primary_route"):
            ctx["routing"] = dict(shadow)

    return ctx


def mirror_concierge_intent(
    session: Any,
    sid: str | None,
    intent: str,
    *,
    topic: str | None = None,
) -> None:
    """v2 セッションで concierge_state 更新を dialogue_state.concierge に dual-write。"""
    from config.llm_flags import is_chat_pipeline_v2_for_session

    if not is_chat_pipeline_v2_for_session(sid):
        return

    ctx = load_dialogue_context(session)
    conc = ctx.setdefault("concierge", {})
    conc["last_intent"] = intent
    if topic is not None:
        conc["topic"] = topic
    try:
        from src.agents.concierge_agent import get_concierge_state

        state = get_concierge_state(session)
        conc["off_topic_turns"] = int(state.get("off_topic_turns") or 0)
    except (TypeError, ValueError, ImportError):
        conc["off_topic_turns"] = 0
    save_dialogue_context(session, ctx)


def save_dialogue_context(
    session: Any,
    ctx: dict[str, Any],
    *,
    dual_write: bool = True,
) -> None:
    """dialogue_state を保存し、移行期はレガシー field を mirror する。"""
    if session is None or not hasattr(session, "__setitem__"):
        return

    session[DIALOGUE_STATE_KEY] = ctx
    if not dual_write:
        return

    pending = (ctx.get("pending") or {}).get("session_delete")
    if pending:
        owner = None
        existing = session.get("pending_memory_delete")
        if isinstance(existing, dict):
            owner = existing.get("owner")
        session["pending_memory_delete"] = {
            "scope": pending.get("scope") or "all",
            "owner": owner,
        }
    elif "pending_memory_delete" in session:
        session.pop("pending_memory_delete", None)

    conc = ctx.get("concierge") or {}
    if conc:
        state = session.setdefault("concierge_state", {})
        if isinstance(state, dict):
            if conc.get("last_intent") is not None:
                state["last_intent"] = conc["last_intent"]
            if conc.get("topic") is not None:
                state["topic"] = conc["topic"]
            if conc.get("off_topic_turns") is not None:
                try:
                    state["off_topic_turns"] = int(conc["off_topic_turns"])
                except (TypeError, ValueError):
                    pass

    if ctx.get("flags", {}).get("fever_context"):
        session["_fever_context_active"] = True

    counseling = ctx.get("counseling") or {}
    if counseling:
        mode = session.setdefault("counseling_mode", {})
        if isinstance(mode, dict):
            if "active" in counseling:
                mode["active"] = bool(counseling["active"])
            if counseling.get("theme"):
                mode["symptom_type"] = counseling["theme"]

    handoff = ctx.get("handoff") or {}
    if handoff.get("target"):
        session["agent_handoff"] = handoff["target"]

    episode_id = ctx.get("episode_id")
    if episode_id:
        session["episode_id"] = episode_id
