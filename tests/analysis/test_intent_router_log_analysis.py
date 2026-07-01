"""IntentRouter ログ集計テスト。"""
from __future__ import annotations

from src.analysis.intent_router_log_analysis import measure_intent_router_logs


def test_measure_intent_router_logs_empty():
    m = measure_intent_router_logs([])
    assert m["shadow_total"] == 0
    assert m["dispatch_total"] == 0


def test_measure_intent_router_logs_shadow_mismatch():
    rows = [
        {
            "log_type": "dialogue_route_shadow",
            "primary_route": "Physical",
            "resolved_by": "gate",
            "mismatch": True,
            "session_id": "line:U1",
            "user_input": "頭痛い",
            "triage_category": "Other",
        },
        {
            "log_type": "dialogue_route_shadow",
            "primary_route": "Physical",
            "resolved_by": "gate",
            "mismatch": False,
        },
        {
            "log_type": "dialogue_route_dispatch",
            "handler": "physical_agent",
            "handled": True,
        },
        {
            "log_type": "dialogue_route_dispatch",
            "handler": "legacy_fallback",
            "handled": False,
        },
    ]
    m = measure_intent_router_logs(rows)
    assert m["shadow_total"] == 2
    assert m["shadow_mismatch"] == 1
    assert m["shadow_mismatch_rate_pct"] == 50.0
    assert m["dispatch_total"] == 2
    assert m["dispatch_handled"] == 1
    assert m["dispatch_success_rate_pct"] == 50.0


def test_measure_intent_router_logs_dialogue_flags():
    rows = [
        {
            "log_type": "dialogue_route_shadow",
            "primary_route": "Physical",
            "mismatch": False,
            "dialogue_flags": {"fever_context": True},
        },
        {
            "log_type": "dialogue_route_shadow",
            "primary_route": "Physical",
            "mismatch": True,
            "dialogue_flags": {"pending_cancelled_by_physical": True},
        },
    ]
    m = measure_intent_router_logs(rows)
    assert m["shadow_with_fever_context_flag"] == 1
    assert m["shadow_with_pending_cancelled_flag"] == 1


def test_measure_intent_router_logs_dispatch_dialogue_flags():
    rows = [
        {
            "log_type": "dialogue_route_dispatch",
            "handler": "physical_agent",
            "handled": True,
            "dialogue_flags": {"pending_cancelled_by_physical": True},
        },
    ]
    m = measure_intent_router_logs(rows)
    assert m["dispatch_total"] == 1
    assert m["dispatch_with_pending_cancelled_flag"] == 1
