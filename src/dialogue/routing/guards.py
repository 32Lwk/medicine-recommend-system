"""Stage C — post-route guards（Wave 1b）。"""
from __future__ import annotations

from typing import Any

from config.routing_config import triage_confidence_threshold
from src.dialogue.routing.types import RouteDecision


def apply_post_route_guards(
    decision: RouteDecision,
    user_text: str,
    session: Any,
    *,
    sid: str | None = None,
    triage_result: dict[str, Any] | None = None,
) -> RouteDecision:
    """発熱コンテキスト中の store 禁止、低 confidence 時の clarification 等。"""
    from src.services.llm_unavailability import should_block_llm_dependent_reply

    if session is not None and should_block_llm_dependent_reply(session):
        return decision

    from src.utils.input_helpers import (
        has_fever_signal,
        session_has_fever_context,
    )

    fever_active = has_fever_signal(user_text) or (
        session is not None
        and hasattr(session, "get")
        and session_has_fever_context(session)
    )

    if fever_active and decision.primary_route == "Store":
        return RouteDecision(
            primary_route="Physical",
            sub_route="fever_flow",
            confidence=max(decision.confidence, 0.9),
            resolved_by="guard",
            source="fever_blocks_store",
            meta={**decision.meta, "overridden_from": "Store"},
        )

    triage = triage_result or {}
    conf = decision.confidence
    # gate 即決定は triage の低信頼で clarification に落とさない
    if decision.resolved_by != "gate" and triage.get("confidence") is not None:
        conf = min(conf, float(triage.get("confidence") or 0))

    threshold = triage_confidence_threshold()
    if conf < threshold and decision.primary_route in ("Physical", "Concierge", "Unknown"):
        from src.utils.input_helpers import has_explicit_symptom_signal

        if decision.primary_route == "Physical" and (
            fever_active or has_explicit_symptom_signal(user_text)
        ):
            return decision
        if decision.resolved_by == "gate" and decision.confidence >= threshold:
            return decision
        return RouteDecision(
            primary_route=decision.primary_route,
            sub_route="clarification",
            confidence=conf,
            resolved_by="guard",
            source="low_confidence_clarification",
            meta={**decision.meta, "original_sub_route": decision.sub_route},
        )

    if decision.primary_route == "Physical" and decision.sub_route == "medicine_side_effect_qa":
        return decision

    if decision.primary_route == "Physical" and decision.sub_route in (
        "rule_based_recommend",
        None,
    ):
        from src.services.medicine_context_routing import (
            resolve_medicine_context_route_rule,
        )

        ctx_route = resolve_medicine_context_route_rule(
            session if session is not None else {},
            sid,
            user_text,
        )
        if ctx_route == "cold_start_recommend":
            return RouteDecision(
                primary_route="Physical",
                sub_route="rule_based_recommend",
                confidence=max(decision.confidence, 0.9),
                resolved_by="guard",
                source="medicine_context_cold_start_guard",
                meta={**decision.meta, "overridden_from": decision.sub_route},
            )
        if ctx_route == "followup_qa":
            return RouteDecision(
                primary_route="Physical",
                sub_route="medicine_followup_qa",
                confidence=max(decision.confidence, 0.9),
                resolved_by="guard",
                source="medicine_context_followup_guard",
                meta={**decision.meta, "overridden_from": decision.sub_route},
            )
        if ctx_route == "symptom_prompt":
            return RouteDecision(
                primary_route="Physical",
                sub_route="symptom_prompt_sports",
                confidence=max(decision.confidence, 0.88),
                resolved_by="guard",
                source="medicine_context_symptom_prompt_guard",
                meta={**decision.meta, "overridden_from": decision.sub_route},
            )

    return decision
