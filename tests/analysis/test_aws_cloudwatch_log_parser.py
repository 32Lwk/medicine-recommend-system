"""Tests for AWS CloudWatch log parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.aws_cloudwatch_log_parser import (
    LogEntry_from_cloudwatch,
    build_aws_analysis_bundle,
    load_aws_log_entries,
)
from src.analysis.gcp_cloud_run_log_parser import extract_chat_flow, extract_http_errors


@pytest.fixture
def sample_cloudwatch_path(tmp_path: Path) -> Path:
    payload = [
        {
            "timestamp": 1719187200100,
            "message": "2026-06-24 00:00:00,100 - INFO - 📨 POST処理開始 trace_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-001",
        },
        {
            "timestamp": 1719187201200,
            "message": "2026-06-24 00:00:01,200 - INFO -    User Message: headache",
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-002",
        },
        {
            "timestamp": 1719187205300,
            "message": (
                "2026-06-24 00:00:05,000 - INFO - PIPELINE_PERF "
                "{'channel': 'web', 'sid': 'sess1', 'total_ms': 9000.0, "
                "'breakdown': {'before_security': 0, 'after_security': 3, 'before_triage': 3}, "
                "'llm': {'llm_calls': [{'path': 'llm_triage.stage1', 'cost_jpy': 0.1, 'latency_ms': 100, 'model': 'gpt-test'}], "
                "'llm_session_cost_jpy': 0.1}}"
            ),
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-003",
        },
        {
            "timestamp": 1719187206300,
            "message": "2026-06-24 00:00:06,300 - ERROR - Internal server error",
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-004",
        },
        {
            "timestamp": 1719187206400,
            "message": "{",
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005a",
        },
        {
            "timestamp": 1719187206401,
            "message": '  "log_type": "counseling_detail",',
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005b",
        },
        {
            "timestamp": 1719187206402,
            "message": '  "timestamp": "2026-06-24T00:00:04",',
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005c",
        },
        {
            "timestamp": 1719187206403,
            "message": '  "session_id": "sess1",',
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005d",
        },
        {
            "timestamp": 1719187206404,
            "message": '  "user_input": "headache",',
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005e",
        },
        {
            "timestamp": 1719187206405,
            "message": '  "response": "Hello! Feel free to ask about OTC medicine anytime."',
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005f",
        },
        {
            "timestamp": 1719187206406,
            "message": "}",
            "logStreamName": "ecs/medicine-recommend/abc123def456",
            "eventId": "evt-005g",
        },
    ]
    path = tmp_path / "downloaded-aws-logs-sample.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_log_entry_from_cloudwatch_severity() -> None:
    entry = LogEntry_from_cloudwatch(
        {"timestamp": 1719187200100, "message": "2026-06-24 00:00:00,100 - ERROR - boom", "eventId": "x"},
        log_group="/ecs/medicine-recommend",
    )
    assert entry.severity == "ERROR"
    assert entry.resource["labels"]["log_group"] == "/ecs/medicine-recommend"


def test_load_and_chat_flow(sample_cloudwatch_path: Path) -> None:
    entries = load_aws_log_entries(sample_cloudwatch_path, log_group="/ecs/medicine-recommend")
    assert len(entries) == 11
    flow = extract_chat_flow(entries)
    assert flow["trace_count"] == 1
    assert flow["exported_traces"][0]["user_message"] == "headache"


def test_build_aws_analysis_bundle_metadata(sample_cloudwatch_path: Path) -> None:
    bundle = build_aws_analysis_bundle(
        sample_cloudwatch_path,
        log_group="/ecs/medicine-recommend",
        region="ap-northeast-1",
    )
    meta = bundle["metadata"]
    assert meta["platform"] == "aws"
    assert meta["log_group"] == "/ecs/medicine-recommend"
    assert meta["entry_count"] == 11
    assert "sections" in bundle
    assert bundle["sections"]["user_sessions"]["counseling_detail_count"] >= 1


def test_text_errors_extracted(sample_cloudwatch_path: Path) -> None:
    entries = load_aws_log_entries(sample_cloudwatch_path)
    from src.analysis.gcp_cloud_run_log_parser import extract_text_errors

    errors = extract_text_errors(entries)
    assert errors["count"] >= 1
