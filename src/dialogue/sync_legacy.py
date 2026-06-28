"""レガシー session フィールド ↔ dialogue_state の同期（Wave 2 移行期）。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.llm_flags import is_chat_pipeline_v2_for_session
from src.dialogue.context import load_dialogue_context, save_dialogue_context

logger = logging.getLogger(__name__)


def mirror_counseling_mode(session: Any, sid: str | None) -> None:
    """counseling_mode → dialogue_state.counseling（v2 セッションのみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return

    counseling_mode = session.get("counseling_mode")
    if not isinstance(counseling_mode, dict):
        return

    ctx = load_dialogue_context(session)
    c = ctx.setdefault("counseling", {})
    c["active"] = bool(counseling_mode.get("active"))
    theme = counseling_mode.get("symptom_type") or counseling_mode.get("theme")
    if theme:
        c["theme"] = str(theme)
    save_dialogue_context(session, ctx)


def mirror_handoff(session: Any, sid: str | None) -> None:
    """agent_handoff → dialogue_state.handoff（v2 セッションのみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return

    target = session.get("agent_handoff")
    if not target:
        return

    ctx = load_dialogue_context(session)
    h = ctx.setdefault("handoff", {})
    h["target"] = str(target)
    if sid and str(sid).startswith("line:"):
        h["active_channel"] = "line"
    elif sid:
        h["active_channel"] = "web"
    h["last_switch_at"] = datetime.now(timezone.utc).isoformat()
    save_dialogue_context(session, ctx)


def clear_pending_medical_cancel_flag(session: Any, sid: str | None) -> None:
    """Physical dispatch 成功後に one-shot フラグをクリア。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    ctx = load_dialogue_context(session)
    flags = ctx.setdefault("flags", {})
    if flags.pop("pending_cancelled_by_physical", None):
        save_dialogue_context(session, ctx)


def mirror_concierge_state(session: Any, sid: str | None) -> None:
    """concierge_state → dialogue_state.concierge（v2 のみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    try:
        from src.agents.concierge_agent import get_concierge_state

        state = get_concierge_state(session)
    except Exception:
        return
    ctx = load_dialogue_context(session)
    conc = ctx.setdefault("concierge", {})
    if state.get("last_intent"):
        conc["last_intent"] = str(state["last_intent"])
    try:
        conc["off_topic_turns"] = int(state.get("off_topic_turns") or 0)
    except (TypeError, ValueError):
        conc["off_topic_turns"] = 0
    save_dialogue_context(session, ctx)


def mirror_fever_context(session: Any, sid: str | None) -> None:
    """_fever_context_active → dialogue_state.flags.fever_context（v2 のみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    if not session.get("_fever_context_active"):
        return
    ctx = load_dialogue_context(session)
    ctx.setdefault("flags", {})["fever_context"] = True
    save_dialogue_context(session, ctx)


def mirror_pending_medical_cancel(session: Any, sid: str | None) -> None:
    """SessionAgent pending 解消時の flags.pending_cancelled_by_physical を立てる。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    ctx = load_dialogue_context(session)
    pending = ctx.setdefault("pending", {})
    pending.pop("session_delete", None)
    ctx.setdefault("flags", {})["pending_cancelled_by_physical"] = True
    save_dialogue_context(session, ctx)


def mirror_pending_session_delete(session: Any, sid: str | None) -> None:
    """pending_memory_delete ↔ dialogue_state.pending.session_delete（v2 のみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    ctx = load_dialogue_context(session)
    save_dialogue_context(session, ctx)


def sync_dialogue_legacy_mirrors(session: Any, sid: str | None) -> None:
    """routing 同期タイミングで legacy → dialogue_state を反映。"""
    try:
        mirror_fever_context(session, sid)
        mirror_pending_session_delete(session, sid)
        mirror_counseling_mode(session, sid)
        mirror_handoff(session, sid)
        mirror_concierge_state(session, sid)
    except Exception:
        logger.debug("sync_dialogue_legacy_mirrors skipped", exc_info=True)


def mark_correction_in_dialogue_state(
    session: Any,
    sid: str | None,
    user_text: str,
) -> None:
    """correction 検出時に dialogue_state.flags.correction_detected を立てる（v2 のみ）。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return
    if session is None or not hasattr(session, "get"):
        return
    from src.utils.input_helpers import detect_correction_intent

    if not detect_correction_intent(user_text):
        return
    ctx = load_dialogue_context(session)
    ctx.setdefault("flags", {})["correction_detected"] = True
    save_dialogue_context(session, ctx)
