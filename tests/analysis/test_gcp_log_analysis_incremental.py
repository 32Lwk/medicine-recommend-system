"""Tests for incremental GCP log analysis improvements."""

from __future__ import annotations

from src.analysis.quality_metrics import build_quality_metrics
from src.analysis.session_conversation_analysis import (
    build_session_conversations,
    dedupe_counseling_details,
)


def test_dedupe_counseling_details() -> None:
    rows = [
        {"session_id": "s1", "timestamp": "t1", "user_input": "a", "response": "r"},
        {"session_id": "s1", "timestamp": "t1", "user_input": "a", "response": "r"},
        {"session_id": "s1", "timestamp": "t2", "user_input": "b", "response": "r2"},
    ]
    deduped, removed = dedupe_counseling_details(rows)
    assert removed == 1
    assert len(deduped) == 2


def test_conversation_history_rebuilt() -> None:
    counseling = [
        {"timestamp": "t1", "session_id": "s1", "user_input": "hi", "response": "hello"},
        {"timestamp": "t2", "session_id": "s1", "user_input": "head pain", "response": "sorry"},
    ]
    result = build_session_conversations(counseling, {"exported_traces": []})
    session = result["sessions"][0]
    assert len(session["conversation_history"]) == 4
    assert session["turns"][1]["conversation_history"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    assert session["turns"][0]["llm_review_required"] is True


def test_quality_metrics_from_bundle() -> None:
    bundle = {
        "sections": {
            "user_sessions": {
                "counseling_detail_count": 10,
                "counseling_details_exported": 8,
                "session_conversations": {
                    "session_count": 1,
                    "exported_session_count": 1,
                    "mismatch_count": 2,
                    "sessions_by_grade": {"poor": 1},
                    "intent_mismatches": [
                        {"issue_type": "x", "severity": "critical"},
                        {"issue_type": "x", "severity": "warning"},
                    ],
                    "physical_recommendation_events": [],
                    "sessions": [
                        {
                            "physical_recommendation_summary": {"physical_turn_count": 1},
                        }
                    ],
                },
            },
            "errors_http": {"http": {"http_4xx_5xx_total": 3, "by_status": {"503": 3}}},
        }
    }
    metrics = build_quality_metrics(bundle)
    assert metrics["conversation"]["heuristic_mismatch_count"] == 2
    assert metrics["conversation"]["physical_sessions_with_advisor_hook"] == 1
    assert metrics["infra"]["http_4xx_5xx_total"] == 3
