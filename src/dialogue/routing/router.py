"""IntentRouter 統合エントリ（Wave 1b + unified pipeline + Jev Phase 1 shadow）。"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from src.dialogue.routing.legacy_router import resolve_legacy_route
from src.dialogue.routing.types import RouteDecision
from src.dialogue.routing.unified_router import resolve_route_unified_or_legacy

logger = logging.getLogger(__name__)

# Optional session/dialogue_state/triage keys that may already hold focus.
# chat_post_pipeline currently keeps focuses in a local var + request_scope_cache
# and does NOT persist them on session; missing → None (no focus LLM for Jev).
_MEDICINE_QA_FOCUS_KEYS: tuple[str, ...] = (
    "medicine_qa_focus",
    "medicine_qa_focuses",
    "qa_focuses",
)


def _focus_from_mapping(data: Any) -> Any | None:
    if not isinstance(data, dict):
        return None
    for key in _MEDICINE_QA_FOCUS_KEYS:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple)) and not value:
            continue
        return value
    return None


def _read_existing_medicine_qa_focus(
    session: Any,
    triage_result: dict[str, Any] | None,
) -> Any | None:
    """session / dialogue_state / triage に既にある focus のみ返す。

    Jev のために ``infer_medicine_qa_focuses`` / focus LLM は呼ばない。
    現行 pipeline は focus を session に書いていないため、通常は None。
    """
    try:
        found = _focus_from_mapping(session) if session is not None else None
        if found is not None:
            return found

        if session is not None and hasattr(session, "get"):
            raw_ds = session.get("dialogue_state")
            found = _focus_from_mapping(raw_ds)
            if found is not None:
                return found
            try:
                from src.dialogue.context import load_dialogue_context

                ctx = load_dialogue_context(session)
                found = _focus_from_mapping(ctx)
                if found is not None:
                    return found
            except Exception:
                pass

        found = _focus_from_mapping(triage_result)
        if found is not None:
            return found
    except Exception:
        logger.debug("medicine_qa_focus session read skipped", exc_info=True)
    return None


def _deterministic_signals_from_context(
    *,
    legacy: RouteDecision,
    triage_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """既存 gate / legacy の高リスク陽性を shadow 比較用に伝える（実行は変えない）。"""
    signals: dict[str, Any] = {}
    triage = triage_result or {}
    primary = legacy.primary_route
    sub = legacy.sub_route

    if primary == "Security":
        signals["security_blocked"] = True
        if sub:
            signals["security_sub_route"] = sub
    if primary == "Emergency":
        signals["emergency_detected"] = True
        if sub:
            signals["emergency_sub_route"] = sub

    category = str(triage.get("category") or "").strip().lower()
    subcategory = str(triage.get("subcategory") or "").strip().lower()
    if category == "emergency" or "medical_examination" in subcategory:
        if "medical_examination" in subcategory or triage.get("medical_examination"):
            signals["medical_examination"] = True
        signals["emergency_detected"] = True
        if sub and "emergency_sub_route" not in signals:
            signals["emergency_sub_route"] = sub
    return signals


def _maybe_schedule_jev_shadow(
    *,
    user_text: str,
    session: Any,
    sid: str | None,
    triage_result: dict[str, Any] | None,
    legacy: RouteDecision,
) -> str | None:
    """legacy 確定後に Jev shadow を 1 回 schedule。失敗しても本線へ影響しない。

    Phase 1: 常に legacy を返す前提。PRIMARY flag が true でも decision は変えない。
    Returns correlation_id when scheduled (or attempted), else None.
    """
    try:
        from config.llm_flags import is_jev_intent_router_shadow_enabled

        if not is_jev_intent_router_shadow_enabled():
            if session is not None and hasattr(session, "pop"):
                try:
                    session.pop("_jev_shadow_correlation_id", None)
                except Exception:
                    pass
            return None

        from src.dialogue.routing.jev_router import (
            build_jev_router_state,
            schedule_jev_shadow,
        )

        correlation_id = str(uuid.uuid4())
        # Focus: read-only from session/dialogue_state/triage if already present.
        # No stable writer in chat_post_pipeline yet → typically None (allowed).
        medicine_qa_focus = _read_existing_medicine_qa_focus(session, triage_result)
        state = build_jev_router_state(
            user_text,
            session,
            sid,
            triage_result=triage_result,
            medicine_qa_focus=medicine_qa_focus,
        )
        scheduled = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id=correlation_id,
            deterministic_signals=_deterministic_signals_from_context(
                legacy=legacy,
                triage_result=triage_result,
            ),
            sid=sid,
        )
        if not scheduled:
            return None
        return correlation_id
    except Exception:
        logger.debug("jev shadow schedule skipped", exc_info=True)
        return None


def resolve_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """Unified pipeline（flag ON）または legacy 2 段 gate → LLM/legacy + post guards。

    Phase 1 Jev: legacy 確定後に shadow を schedule し、常に同一 legacy を返す。
    ``JEV_INTENT_ROUTER_PRIMARY`` は Phase 1 では実行 decision に影響させない。
    """
    legacy = resolve_route_unified_or_legacy(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )

    correlation_id = _maybe_schedule_jev_shadow(
        user_text=user_text,
        session=session,
        sid=sid,
        triage_result=triage_result,
        legacy=legacy,
    )
    if session is not None and hasattr(session, "__setitem__"):
        try:
            if correlation_id:
                # dispatcher が executed を join するための短い相関キー（routing 決定ではない）
                session["_jev_shadow_correlation_id"] = correlation_id
            elif hasattr(session, "pop"):
                session.pop("_jev_shadow_correlation_id", None)
        except Exception:
            logger.debug("jev correlation_id stash skipped", exc_info=True)

    # Phase 1 invariant: never return a Jev decision (PRIMARY flag ignored).
    return legacy


def _legacy_resolve_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """Backward-compatible alias."""
    return resolve_legacy_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
