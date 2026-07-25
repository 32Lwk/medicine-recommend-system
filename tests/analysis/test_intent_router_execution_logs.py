"""dialogue_route_execution ログ集計テスト。"""
from __future__ import annotations

from src.analysis.intent_router_log_analysis import measure_intent_router_logs


def test_measure_execution_logs():
    rows = [
        {
            "log_type": "dialogue_route_execution",
            "dispatch_sub_route": "medicine_side_effect_qa",
            "mismatch": False,
            "layer_used": "layer1",
        },
        {
            "log_type": "dialogue_route_execution",
            "dispatch_sub_route": "app_about",
            "resolved_execution_intent": "doc_changelog",
            "mismatch": True,
            "layer_used": "layer3",
        },
    ]
    metrics = measure_intent_router_logs(rows)
    assert metrics["execution_total"] == 2
    assert metrics["execution_mismatch"] == 1
    assert metrics["execution_side_effect_qa"] == 1
    assert metrics["execution_by_layer_used"]["layer1"] == 1
