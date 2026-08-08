"""resolve_medicine_qa_route — 医薬品スレッド中の Concierge 話題転換。"""
from __future__ import annotations


def test_architecture_pivot_beats_intent_router_medicine_sub():
    from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

    session = {
        "_intent_router_dispatch": {
            "primary_route": "Physical",
            "sub_route": "medicine_side_effect_qa",
        },
        "messages": [
            {"type": "user", "content": "ロキソニンの副作用教えて"},
            {
                "type": "bot",
                "content": "副作用の要点です",
                "diagnosis": {"kind": "medicine_side_effect_qa"},
            },
        ],
    }
    decision = resolve_medicine_qa_route(
        "技術スタックは？",
        session=session,
        conversation_history=session["messages"],
    )
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "architecture"


def test_skip_focus_llm_for_rule_thread_route():
    from src.services.medicine_qa_eligibility import (
        MedicineQaRoute,
        MedicineQaRouteDecision,
        should_skip_focus_llm_enrichment,
    )

    assert should_skip_focus_llm_enrichment(
        MedicineQaRouteDecision(MedicineQaRoute.CONCIERGE, "topic_pivot_concierge")
    )
    assert should_skip_focus_llm_enrichment(
        MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            "rule_medicine_thread_continuation",
        )
    )
    assert not should_skip_focus_llm_enrichment(
        MedicineQaRouteDecision(MedicineQaRoute.DEFER, "empty")
    )
