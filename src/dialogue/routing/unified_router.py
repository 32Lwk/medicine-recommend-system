"""Unified routing pipeline — gate/router/follow-up を単一 RoutingDecision に集約。"""
from __future__ import annotations

import logging
from typing import Any

from config.llm_flags import is_unified_router_enabled
from src.dialogue.routing.context_signals import (
    ContextFeatures,
    extract_context_features,
    is_explicit_new_meta_topic,
    is_medicine_side_effect_question,
)
from src.dialogue.routing.follow_up_llm import resolve_follow_up_route
from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.legacy_router import resolve_legacy_route
from src.dialogue.routing.routing_decision import RoutingDecision, coerce_routing_decision
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)


def _summarize_recent_turns(session: Any, *, limit: int = 5) -> str:
    messages = (session or {}).get("messages") or []
    lines: list[str] = []
    for msg in messages[-limit:]:
        if not isinstance(msg, dict):
            continue
        role = "user" if msg.get("type") == "user" else "bot"
        content = str(msg.get("content") or msg.get("message") or "")[:120]
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _layer1_deterministic(
    user_text: str,
    features: ContextFeatures,
) -> RoutingDecision | None:
    text = (user_text or "").strip()

    if features.is_side_effect_question or is_medicine_side_effect_question(text):
        return RoutingDecision(
            primary_route="Physical",
            sub_route="medicine_side_effect_qa",
            confidence=0.96,
            resolved_by="gate",
            source="layer1_side_effect_qa",
            execution_lock=True,
            layer_used="layer1",
            context_features=features.to_dict(),
        )

    prior = features.prior_route or features.prior_concierge_intent
    if prior == "doc_changelog" and is_explicit_new_meta_topic(text, prior_intent=prior):
        sub = "app_about" if _looks_app_about(text) else "architecture"
        return RoutingDecision(
            primary_route="Concierge",
            sub_route=sub,
            confidence=0.94,
            resolved_by="gate",
            source="layer1_topic_break",
            execution_lock=True,
            layer_used="layer1",
            context_features=features.to_dict(),
            follow_up={"topic_break": True, "prior": prior},
        )

    if features.is_doc_changelog_continuation and prior == "doc_changelog":
        return RoutingDecision(
            primary_route="Concierge",
            sub_route="doc_changelog",
            confidence=0.93,
            resolved_by="gate",
            source="layer1_changelog_continue",
            execution_lock=True,
            layer_used="layer1",
            context_features=features.to_dict(),
        )

    return None


def _looks_app_about(text: str) -> bool:
    import re

    return bool(
        re.search(
            r"あなた|サービス|アプリ|Sage\s*Terrace|何が(?:できる|出来る)",
            text or "",
            re.IGNORECASE,
        )
    )


def _apply_follow_up_layer(
    user_text: str,
    session: Any,
    sid: str | None,
    features: ContextFeatures,
    base: RoutingDecision,
    *,
    client: Any = None,
) -> RoutingDecision:
    if not features.is_ambiguous_short_follow_up:
        return base

    prior = features.prior_route or features.prior_concierge_intent
    if prior and is_explicit_new_meta_topic(user_text, prior_intent=prior):
        return base

    follow = resolve_follow_up_route(
        user_text,
        features,
        session=session,
        client=client,
        recent_turns=_summarize_recent_turns(session),
    )
    if follow is None:
        return base

    return RoutingDecision.from_route_decision(
        follow,
        execution_lock=True,
        layer_used="layer3",
        context_features=features.to_dict(),
        follow_up={"source": follow.source},
    )


def _store_decision(session: Any, decision: RoutingDecision) -> None:
    if session is None or not hasattr(session, "__setitem__"):
        return
    session["_intent_router_shadow"] = decision.to_dialogue_routing_dict()
    session["_routing_decision"] = decision.to_dialogue_routing_dict()
    if decision.execution_lock:
        session["_routing_execution_lock"] = True
    if decision.primary_route == "Concierge" and decision.sub_route:
        session["last_concierge_intent"] = decision.sub_route


def resolve_unified_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RoutingDecision:
    """3層ハイブリッド unified routing。"""
    features = extract_context_features(user_text, session, sid)

    layer1 = _layer1_deterministic(user_text, features)
    if layer1 is not None:
        decision = apply_post_route_guards(
            layer1,
            user_text,
            session,
            sid=sid,
            triage_result=triage_result,
        )
        final = coerce_routing_decision(decision)
        if not isinstance(decision, RoutingDecision):
            final = RoutingDecision.from_route_decision(
                decision,
                execution_lock=layer1.execution_lock,
                layer_used=layer1.layer_used,
                context_features=features.to_dict(),
            )
        _store_decision(session, final)
        return final

    base_decision = resolve_legacy_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
    routing = RoutingDecision.from_route_decision(
        base_decision,
        layer_used="layer2",
        context_features=features.to_dict(),
    )

    if features.is_ambiguous_short_follow_up:
        routing = _apply_follow_up_layer(
            user_text,
            session,
            sid,
            features,
            routing,
            client=client,
        )

    guarded = apply_post_route_guards(
        routing,
        user_text,
        session,
        sid=sid,
        triage_result=triage_result,
    )
    final = coerce_routing_decision(guarded)
    if not isinstance(guarded, RoutingDecision):
        final = RoutingDecision.from_route_decision(
            guarded,
            execution_lock=routing.execution_lock,
            layer_used=routing.layer_used,
            context_features=features.to_dict(),
            follow_up=routing.follow_up,
        )
    _store_decision(session, final)
    return final


def resolve_route_unified_or_legacy(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """Feature flag に応じて unified / legacy を切り替え。"""
    if is_unified_router_enabled(sid):
        return resolve_unified_route(
            user_text,
            session,
            sid,
            triage_result=triage_result,
            client=client,
        )
    return resolve_legacy_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
