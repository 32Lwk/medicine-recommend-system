"""Phase 4a-1: shadow mismatch 分類タグのテスト。"""
from __future__ import annotations

from src.analysis.intent_router_log_analysis import measure_intent_router_logs
from src.dialogue.routing.shadow_mismatch import classify_shadow_mismatch, infer_mismatch_kind_from_log
from src.dialogue.routing.types import RouteDecision


def _decision(
    primary_route: str,
    *,
    resolved_by: str = "gate",
    sub_route: str | None = None,
) -> RouteDecision:
    return RouteDecision(
        primary_route=primary_route,  # type: ignore[arg-type]
        sub_route=sub_route,
        confidence=0.9,
        resolved_by=resolved_by,  # type: ignore[arg-type]
    )


def test_physical_physical_agrees():
    mismatch, kind = classify_shadow_mismatch(
        _decision("Physical"),
        {"category": "Physical"},
    )
    assert mismatch is False
    assert kind is None


def test_other_physical_gate_improvement():
    mismatch, kind = classify_shadow_mismatch(
        _decision("Physical", resolved_by="gate"),
        {"category": "Other", "subcategory": "general_other"},
    )
    assert mismatch is True
    assert kind == "gate_improvement"


def test_other_store_gate_improvement():
    mismatch, kind = classify_shadow_mismatch(
        _decision("Store", resolved_by="guard"),
        {"category": "Other"},
    )
    assert mismatch is True
    assert kind == "gate_improvement"


def test_other_physical_fever_context_exempt():
    session = {
        "dialogue_state": {
            "version": 1,
            "flags": {"fever_context": True},
        }
    }
    mismatch, kind = classify_shadow_mismatch(
        _decision("Physical", resolved_by="gate"),
        {"category": "Other"},
        session,
    )
    assert mismatch is False
    assert kind == "exempt"


def test_other_concierge_regression():
    mismatch, kind = classify_shadow_mismatch(
        _decision("Physical", resolved_by="llm"),
        {"category": "Other"},
    )
    assert mismatch is True
    assert kind == "regression"


def test_ask_counseling_regression_without_counseling_context():
    mismatch, kind = classify_shadow_mismatch(
        _decision("Counseling", resolved_by="gate"),
        {"category": "Ask"},
    )
    assert mismatch is True
    assert kind == "regression"


def test_ask_counseling_exempt_when_counseling_mode_active():
    session = {"counseling_mode": {"active": True, "symptom_type": "insomnia"}}
    mismatch, kind = classify_shadow_mismatch(
        _decision(
            "Counseling",
            resolved_by="gate",
            sub_route="counseling_continue",
        ),
        {"category": "Ask"},
        session,
    )
    assert mismatch is False
    assert kind == "exempt"


def test_ask_counseling_exempt_when_gate_counseling_pending_answer():
    mismatch, kind = classify_shadow_mismatch(
        RouteDecision(
            primary_route="Counseling",
            sub_route="counseling_continue",
            confidence=0.92,
            resolved_by="gate",
            source="counseling_pending_answer",
        ),
        {"category": "Ask"},
    )
    assert mismatch is False
    assert kind == "exempt"


def test_infer_mismatch_kind_counseling_followup_exempt_row():
    row = {
        "mismatch": True,
        "mismatch_kind": "regression",
        "triage_category": "Ask",
        "primary_route": "Counseling",
        "sub_route": "emotional_support",
        "user_input": "2週間くらいです",
        "resolved_by": "llm",
    }
    assert infer_mismatch_kind_from_log(row) == "exempt"
    row = {
        "mismatch": True,
        "triage_category": "Other",
        "primary_route": "Physical",
        "resolved_by": "gate",
    }
    assert infer_mismatch_kind_from_log(row) == "gate_improvement"


def test_measure_intent_router_logs_includes_new_rates():
    rows = [
        {
            "log_type": "dialogue_route_shadow",
            "mismatch": True,
            "mismatch_kind": "gate_improvement",
            "triage_category": "Other",
            "primary_route": "Physical",
            "resolved_by": "gate",
        },
        {
            "log_type": "dialogue_route_shadow",
            "mismatch": True,
            "mismatch_kind": "regression",
            "triage_category": "Other",
            "primary_route": "Counseling",
            "resolved_by": "gate",
        },
        {
            "log_type": "dialogue_route_shadow",
            "mismatch": False,
            "mismatch_kind": "exempt",
            "triage_category": "Other",
            "primary_route": "Physical",
            "dialogue_flags": {"fever_context": True},
        },
        {
            "log_type": "dialogue_route_shadow",
            "mismatch": False,
            "triage_category": "Physical",
            "primary_route": "Physical",
        },
    ]
    metrics = measure_intent_router_logs(rows)
    assert metrics["shadow_total"] == 4
    assert metrics["shadow_mismatch"] == 2
    assert metrics["shadow_mismatch_rate_pct"] == 50.0
    assert metrics["shadow_improvement_mismatch"] == 1
    assert metrics["shadow_improvement_mismatch_rate_pct"] == 25.0
    assert metrics["shadow_regression_mismatch"] == 1
    assert metrics["shadow_regression_mismatch_rate_pct"] == 25.0
    assert metrics["shadow_exempt"] == 1
    assert "shadow_by_mismatch_kind" in metrics
