"""Tests for session transcript markdown."""

from __future__ import annotations

from src.analysis.session_transcript_markdown import (
    build_turn_timing,
    render_session_transcript_markdown,
    summarize_pipeline_breakdown,
)


def test_summarize_breakdown() -> None:
    b = {
        "post_start": 0,
        "before_security": 0,
        "after_security": 900,
        "before_triage": 900,
        "after_triage": 4000,
        "concierge_build_payload_start": 5000,
        "concierge_build_payload_end": 8000,
    }
    s = summarize_pipeline_breakdown(b)
    assert s["security_ms"] == 900
    assert s["triage_ms"] == 3100
    assert s["concierge_build_ms"] == 3000


def test_build_turn_timing() -> None:
    trace = {
        "started_at": "2026-06-24T02:45:14.065458Z",
        "pipeline_perf": {
            "total_ms": 9963.0,
            "breakdown": {"post_start": 0, "after_security": 100},
            "llm": {
                "llm_calls": [{"path": "llm_triage.stage1", "model": "gpt-test", "latency_ms": 100, "cost_jpy": 0.1}],
                "llm_call_count": 1,
            },
        },
    }
    timing = build_turn_timing(
        trace=trace,
        response_at="2026-06-24T02:45:22.205323",
        previous_response_at="2026-06-23T23:49:39.987788",
    )
    assert timing["pipeline_total_ms"] == 9963.0
    assert timing["e2e_ms"] is not None
    assert timing["since_previous_turn_ms"] is not None
    assert timing["llm_call_count"] == 1


def test_render_session_markdown_contains_transcript() -> None:
    session = {
        "session_id": "line:Utest",
        "channel": "line",
        "time_range": {"start": "2026-06-24T00:00:00", "end": "2026-06-24T00:01:00"},
        "evaluation": {"overall_grade": "good"},
        "turns": [
            {
                "user_input": "headache",
                "response_preview": "please describe more",
                "timing": {
                    "user_message_at": "2026-06-24T00:00:01Z",
                    "response_at": "2026-06-24T00:00:09Z",
                    "e2e_ms": 8000,
                    "pipeline_total_ms": 7500,
                    "phase_summary_ms": {"triage_ms": 2000},
                    "llm_calls": [],
                },
                "routing": {"trace_id": "abc"},
            }
        ],
    }
    md = render_session_transcript_markdown(session)
    assert "headache" in md
    assert "please describe more" in md
    assert "E2E" in md or "受信→返信" in md
    assert "ターン 1" in md
