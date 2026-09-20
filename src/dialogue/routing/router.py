"""IntentRouter 統合エントリ（Wave 1b + unified pipeline + Jev Phase 1 shadow）。"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from src.dialogue.routing.legacy_router import resolve_legacy_route
from src.dialogue.routing.types import RouteDecision
from src.dialogue.routing.unified_router import resolve_route_unified_or_legacy

logger = logging.getLogger(__name__)


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
        state = build_jev_router_state(
            user_text,
            session,
            sid,
            triage_result=triage_result,
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
