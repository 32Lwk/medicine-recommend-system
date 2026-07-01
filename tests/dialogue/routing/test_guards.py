"""post-route guards テスト。"""
from __future__ import annotations

from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.types import RouteDecision


def test_fever_blocks_store_guard():
    session = {
        "messages": [{"type": "user", "content": "39度の熱があります"}],
        "_fever_context_active": True,
    }
    decision = RouteDecision(
        primary_route="Store",
        sub_route="store_locator",
        confidence=0.9,
        resolved_by="gate",
    )
    out = apply_post_route_guards(decision, "近くの薬局", session)
    assert out.primary_route == "Physical"
    assert out.sub_route == "fever_flow"
    assert out.resolved_by == "guard"


def test_physical_symptom_skips_low_confidence_clarification():
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.3,
        resolved_by="llm",
    )
    triage = {"category": "Physical", "confidence": 0.3}
    out = apply_post_route_guards(decision, "頭痛い", {}, triage_result=triage)
    assert out.sub_route == "rule_based_recommend"
    assert out.resolved_by == "llm"


def test_gate_confidence_not_downgraded_by_low_triage():
    decision = RouteDecision(
        primary_route="Concierge",
        sub_route="architecture",
        confidence=0.95,
        resolved_by="gate",
    )
    triage = {"category": "Other", "confidence": 0.2}
    out = apply_post_route_guards(decision, "技術スタックは？", {}, triage_result=triage)
    assert out.sub_route == "architecture"
    assert out.resolved_by == "gate"


def test_low_confidence_triggers_clarification_without_symptom():
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.3,
        resolved_by="llm",
    )
    triage = {"category": "Physical", "confidence": 0.3}
    out = apply_post_route_guards(decision, "こんにちは", {}, triage_result=triage)
    assert out.sub_route == "clarification"
    assert out.resolved_by == "guard"
