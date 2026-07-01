"""IntentRouter 統合エントリ（Wave 1b）。"""
from __future__ import annotations

import logging
from typing import Any

from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.intent_router import run_intent_router_llm
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)


def resolve_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """2 段 gate → LLM/legacy + post guards。"""
    gate = run_deterministic_gate(
        user_text,
        session,
        sid,
        triage_result=triage_result,
    )
    if gate is not None and gate.confidence >= 0.85:
        decision = gate
    else:
        llm = run_intent_router_llm(
            user_text,
            session,
            sid,
            triage_result=triage_result,
            client=client,
            gate_decision=gate,
        )
        decision = llm or RouteDecision(
            primary_route="Unknown",
            sub_route=None,
            confidence=0.0,
            resolved_by="legacy",
            source="unresolved",
        )
        if gate is not None and decision.primary_route == "Unknown":
            decision = gate

    return apply_post_route_guards(
        decision,
        user_text,
        session,
        triage_result=triage_result,
    )
