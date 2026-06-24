"""Tests for GCP Cloud Run log parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.gcp_cloud_run_log_parser import (
    build_analysis_bundle,
    extract_chat_flow,
    extract_http_errors,
    extract_user_sessions,
    load_gcp_log_entries,
)

@pytest.fixture
def sample_entries(tmp_path: Path) -> Path:
    payload = [
        {
            "timestamp": "2026-06-24T00:00:00Z",
            "severity": "INFO",
            "textPayload": "2026-06-24 00:00:00,100 - INFO - 📨 POST処理開始 trace_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "medicine-recommend-dev", "revision_name": "rev-001"},
            },
            "labels": {"commit-sha": "abc123"},
        },
        {
            "timestamp": "2026-06-24T00:00:01Z",
            "textPayload": "2026-06-24 00:00:01,200 - INFO -    User Message: headache",
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "medicine-recommend-dev", "revision_name": "rev-001"},
            },
        },
        {
            "timestamp": "2026-06-24T00:00:02Z",
            "textPayload": "2026-06-24 00:00:02,300 - INFO - LLM triage: Physical, subcategory: headache, confidence: 0.95",
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "medicine-recommend-dev", "revision_name": "rev-001"},
            },
        },
        {
            "timestamp": "2026-06-24T00:00:05Z",
            "textPayload": (
                "2026-06-24 00:00:05,000 - INFO - PIPELINE_PERF "
                "{'channel': 'web', 'sid': 'sess1', 'total_ms': 9000.0, "
                "'breakdown': {'before_security': 0, 'after_security': 3, 'before_triage': 3}, "
                "'llm': {'llm_calls': [{'path': 'llm_triage.stage1', 'cost_jpy': 0.1, 'latency_ms': 100, 'model': 'gpt-test'}], "
                "'llm_session_cost_jpy': 0.1}}"
            ),
        },
        {
            "timestamp": "2026-06-24T00:00:06Z",
            "severity": "ERROR",
            "httpRequest": {
                "requestMethod": "POST",
                "requestUrl": "https://example.run.app/line/webhook",
                "status": 503,
                "latency": "0.050s",
            },
            "resource": {
                "labels": {"service_name": "medicine-recommend-dev", "revision_name": "rev-001"},
            },
        },
        {"textPayload": "{"},
        {"textPayload": '  "log_type": "counseling_detail",'},
        {"textPayload": '  "timestamp": "2026-06-24T00:00:04",'},
        {"textPayload": '  "session_id": "sess1",'},
        {"textPayload": '  "user_input": "headache",'},
        {"textPayload": '  "response": "Hello! Feel free to ask about OTC medicine anytime."'},
        {"textPayload": "}"},
    ]
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_and_http_errors(sample_entries: Path) -> None:
    entries = load_gcp_log_entries(sample_entries)
    http = extract_http_errors(entries)
    assert http["http_4xx_5xx_total"] == 1
    assert http["samples"][0]["status"] == 503


def test_chat_flow_trace(sample_entries: Path) -> None:
    entries = load_gcp_log_entries(sample_entries)
    flow = extract_chat_flow(entries)
    assert flow["trace_count"] == 1
    trace = flow["exported_traces"][0]
    assert trace["user_message"] == "headache"
    assert trace["triage"] is None  # sample uses non-Japanese triage label


def test_counseling_and_session_analysis(sample_entries: Path) -> None:
    entries = load_gcp_log_entries(sample_entries)
    sessions = extract_user_sessions(entries, max_counseling=10)
    assert sessions["counseling_detail_count"] == 1
    sc = sessions["session_conversations"]
    assert sc["session_count"] == 1
    assert len(sc["sessions"][0]["turns"]) == 1
    # headache + greeting response => symptom_ignored or greeting_to_non_greeting
    turn = sc["sessions"][0]["turns"][0]
    assert turn["user_input"] == "headache"
    assert turn["issues"]  # at least one heuristic issue


def test_build_bundle(sample_entries: Path) -> None:
    bundle = build_analysis_bundle(sample_entries, max_traces=10, max_counseling=10)
    assert bundle["metadata"]["primary_service"] == "medicine-recommend-dev"
    assert "pipeline_perf" in bundle["sections"]
    assert bundle["sections"]["llm_cost"]["llm_call_count"] == 1


def test_chat_flow_triage_japanese(tmp_path: Path) -> None:
    payload = [
        {
            "timestamp": "2026-06-24T00:00:00Z",
            "textPayload": "POST trace_id=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        },
        {
            "timestamp": "2026-06-24T00:00:01Z",
            "textPayload": "LLMトリアージ結果: Physical, subcategory: headache, confidence: 0.95",
        },
    ]
    path = tmp_path / "triage.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    flow = extract_chat_flow(load_gcp_log_entries(path))
    assert flow["exported_traces"][0]["triage"]["category"] == "Physical"
