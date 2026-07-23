"""Stage B — LLM IntentRouter（Wave 1b 初期: triage マップ + 将来 LLM）。"""
from __future__ import annotations

from typing import Any

from src.dialogue.routing.types import RouteDecision

_CATEGORY_TO_ROUTE: dict[str, str] = {
    "Physical": "Physical",
    "Emergency": "Emergency",
    "Ask": "Physical",
    "Emotional": "Counseling",
    "Other": "Concierge",
}


def map_triage_to_route(triage_result: dict[str, Any] | None) -> RouteDecision | None:
    """legacy triage 結果を RouteDecision に写像（shadow / 移行期）。"""
    triage = triage_result or {}
    category = str(triage.get("category") or "")
    if not category:
        return None

    sub = str(triage.get("subcategory") or "")
    session_intent = str(triage.get("session_intent") or "").lower()
    if "session_admin" in sub or session_intent in ("delete", "summarize", "status"):
        return RouteDecision(
            primary_route="SessionOps",
            sub_route=session_intent or "session_admin",
            confidence=float(triage.get("confidence") or 0.75),
            resolved_by="legacy",
            source="triage_session_admin",
        )

    concierge_intent = triage.get("concierge_intent")
    if category == "Other" and concierge_intent:
        return RouteDecision(
            primary_route="Concierge",
            sub_route=str(concierge_intent),
            confidence=float(triage.get("confidence") or 0.75),
            resolved_by="legacy",
            source="triage_concierge",
        )

    primary = _CATEGORY_TO_ROUTE.get(category, "Unknown")
    sub_route = sub or None
    if primary == "Physical" and "fever" in sub.lower():
        sub_route = "fever_flow"

    return RouteDecision(
        primary_route=primary,  # type: ignore[arg-type]
        sub_route=sub_route,
        confidence=float(triage.get("confidence") or 0.75),
        resolved_by="legacy",
        source=f"triage_map:{category}",
    )


def run_intent_router_llm(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
    gate_decision: RouteDecision | None = None,
) -> RouteDecision | None:
    """
    Stage B。triage マップ +（フラグ ON 時）structured LLM。
    gate 低信頼決定も候補に含め confidence 最大を採用。
    """
    from src.dialogue.routing.intent_router_llm import (
        call_intent_router_llm,
        pick_best_route_decision,
    )

    from config.llm_flags import is_intent_router_primary_enabled

    legacy = map_triage_to_route(triage_result)
    llm = call_intent_router_llm(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
    primary = is_intent_router_primary_enabled(sid)
    picked = pick_best_route_decision(
        legacy,
        gate_decision,
        llm,
        primary_llm_over_legacy=primary,
    )
    from src.dialogue.routing.intent_router_llm import (
        maybe_correct_concierge_app_about_route,
        maybe_correct_concierge_keyword_meta_route,
    )

    picked = maybe_correct_concierge_keyword_meta_route(
        picked,
        user_text,
        triage_result=triage_result,
    )
    return maybe_correct_concierge_app_about_route(picked, user_text)
