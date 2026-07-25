"""guards — medicine_side_effect_qa 保護テスト。"""
from __future__ import annotations

from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.types import RouteDecision


def test_guard_does_not_override_medicine_side_effect_qa():
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="medicine_side_effect_qa",
        confidence=0.96,
        resolved_by="gate",
        source="layer1_side_effect_qa",
    )
    session = {
        "messages": [
            {
                "type": "bot",
                "diagnosis": {"recommended_medicines": [{"product_name": "カロナールＡ"}]},
            }
        ]
    }
    out = apply_post_route_guards(
        decision,
        "ロキソニンって眠い？",
        session,
        sid="sid",
        triage_result={"category": "Ask", "confidence": 0.3},
    )
    assert out.sub_route == "medicine_side_effect_qa"
