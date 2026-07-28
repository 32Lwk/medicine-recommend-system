"""IntentRouter shadow mode — 観測のみ、dispatch は旧 pipeline（Wave 1b）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

from config.llm_flags import is_intent_router_v2_enabled
from src.dialogue.context import load_dialogue_context, save_dialogue_context
from src.dialogue.routing.metrics import log_dialogue_route_shadow
from src.dialogue.routing.router import resolve_route
from src.dialogue.routing.shadow_mismatch import MismatchKind, classify_shadow_mismatch
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)


def _mismatch(decision: RouteDecision, triage: dict[str, Any], session: Any = None) -> bool:
    mismatch, _kind = classify_shadow_mismatch(decision, triage, session)
    return mismatch


def run_and_record_shadow(
    session: Any,
    sid: str | None,
    user_text: str,
    triage_result: dict[str, Any] | None,
    client: Any = None,
) -> RouteDecision | None:
    """v2 IntentRouter shadow: dialogue_state.routing に記録し legacy dispatch は変更しない。"""
    if not is_intent_router_v2_enabled(sid):
        return None

    decision = resolve_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )

    if session is None or not hasattr(session, "__setitem__"):
        return decision

    ctx = load_dialogue_context(session)
    ctx["routing"] = decision.to_dialogue_routing_dict()
    save_dialogue_context(session, ctx, dual_write=False)

    triage = triage_result or {}
    mismatch, mismatch_kind = classify_shadow_mismatch(decision, triage, session)
    dialogue_flags: dict[str, bool] = {}
    try:
        flags = load_dialogue_context(session).get("flags") or {}
        for key in ("fever_context", "pending_cancelled_by_physical"):
            if flags.get(key):
                dialogue_flags[key] = True
    except Exception:
        pass

    if mismatch:
        logger.info(
            "intent_router_shadow mismatch sid=%s kind=%s decision=%s/%s triage=%s/%s",
            sid,
            mismatch_kind,
            decision.primary_route,
            decision.sub_route,
            triage.get("category"),
            triage.get("subcategory"),
        )
    elif mismatch_kind == "exempt":
        logger.debug(
            "intent_router_shadow exempt sid=%s decision=%s/%s triage=%s/%s",
            sid,
            decision.primary_route,
            decision.sub_route,
            triage.get("category"),
            triage.get("subcategory"),
        )
    else:
        logger.debug(
            "intent_router_shadow agree sid=%s route=%s",
            sid,
            decision.primary_route,
        )

    log_dialogue_route_shadow(
        session_id=sid,
        user_input=user_text,
        decision=decision.to_dialogue_routing_dict(),
        triage_category=triage.get("category"),
        triage_subcategory=triage.get("subcategory"),
        mismatch=mismatch,
        mismatch_kind=mismatch_kind,
        dialogue_flags=dialogue_flags or None,
    )

    session["_intent_router_shadow"] = decision.to_dialogue_routing_dict()
    return decision


def schedule_shadow_observation(
    session: Any,
    sid: str | None,
    user_text: str,
    triage_result: dict[str, Any] | None,
    client: Any = None,
) -> None:
    """IntentRouter shadow を非同期実行（本線ルーティングは変更しない）。"""
    import threading

    def _worker() -> None:
        try:
            run_and_record_shadow(session, sid, user_text, triage_result, client)
        except Exception:
            logger.debug("intent_router_shadow async failed", exc_info=True)

    threading.Thread(target=_worker, daemon=True, name="intent_router_shadow").start()


__all__ = [
    "run_and_record_shadow",
    "schedule_shadow_observation",
    "_mismatch",
    "classify_shadow_mismatch",
    "MismatchKind",
]
