"""Meta / Concierge 経路向け safety_gate 軽量モード判定。"""
from __future__ import annotations

from typing import Any, Optional

_META_SHORTPATH_INTENTS = frozenset({
    "greeting",
    "thanks",
    "redirect",
    "chitchat",
    "app_about",
    "architecture",
    "capabilities",
    "doc_changelog",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "session_ops",
})

_META_SHORTPATH_SUB_ROUTES = _META_SHORTPATH_INTENTS | frozenset({"clarification"})


def is_meta_safety_shortpath_eligible(
    triage_result: Optional[dict[str, Any]],
    session: Any = None,
) -> bool:
    """Other / Concierge meta 応答では emergency LLM 分類をスキップしてよいか。"""
    triage = triage_result or {}
    category = str(triage.get("category") or "").strip()

    intent = str(triage.get("concierge_intent") or "").strip()
    if intent in _META_SHORTPATH_INTENTS:
        return True

    subcategory = str(triage.get("subcategory") or "").strip()
    if subcategory in _META_SHORTPATH_SUB_ROUTES:
        return True

    if session is not None and hasattr(session, "get"):
        shadow = session.get("_intent_router_shadow") or {}
        if isinstance(shadow, dict):
            primary = shadow.get("primary_route")
            sub = shadow.get("sub_route")
            if primary == "Concierge" and sub in _META_SHORTPATH_SUB_ROUTES:
                return True
            if primary == "SessionOps":
                return True

        routing = session.get("_routing_decision") or {}
        if isinstance(routing, dict):
            layer = routing.get("layer_used")
            sub = routing.get("sub_route")
            if layer in ("layer1", "layer3") and sub in _META_SHORTPATH_SUB_ROUTES:
                return True

    if category == "Other" and triage.get("_intent_router_dispatch"):
        if intent in _META_SHORTPATH_INTENTS:
            return True

    return False
