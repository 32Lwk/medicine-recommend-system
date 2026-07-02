"""Phase 4a-3: local_v2_chat_test_runner の IntentRouter KPI 計測。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.local_v2_chat_test_runner import (  # noqa: E402
    _format_intent_router_shadow_section,
    write_intent_router_metrics_json,
    write_report,
)


def test_format_intent_router_shadow_section_includes_4a_kpis():
    metrics = {
        "intent_router_shadow": {
            "sources": {"shadow_jsonl": "log/x.jsonl"},
            "local": {
                "dispatch_success_rate_pct": 92.5,
                "dispatch_handled": 111,
                "dispatch_total": 120,
                "shadow_regression_mismatch_rate_pct": 0.33,
                "shadow_regression_mismatch": 4,
                "shadow_total": 1200,
                "shadow_mismatch_rate_pct": 6.0,
                "shadow_improvement_mismatch_rate_pct": 5.5,
                "shadow_exempt_rate_pct": 1.5,
                "dispatch_unhandled": 9,
                "shadow_by_mismatch_kind": {
                    "agree": 1100,
                    "gate_improvement": 70,
                    "regression": 4,
                    "exempt": 26,
                },
            },
        }
    }
    lines = _format_intent_router_shadow_section(metrics)
    text = "\n".join(lines)
    assert "## IntentRouter Shadow / Dispatch KPI" in text
    assert "dispatch_success_rate_pct" in text
    assert "92.5%" in text
    assert "shadow_regression_mismatch_rate_pct" in text
    assert "0.33%" in text


def test_format_intent_router_shadow_section_skip_metrics():
    lines = _format_intent_router_shadow_section({"intent_router_shadow_skipped": True})
    assert "--skip-metrics" in "\n".join(lines)


def test_write_intent_router_metrics_json(tmp_path: Path):
    meta = {"date": "2026-07-02", "report_suffix": "p4a-metrics-test", "scenario_count": 3}
    metrics = {
        "intent_router_shadow": {
            "sources": {"shadow_jsonl": "log/dialogue_route_shadow_log.jsonl"},
            "local": {"dispatch_success_rate_pct": 90.0},
        }
    }
    out = tmp_path / "metrics.json"
    write_intent_router_metrics_json(meta, metrics, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["meta"]["report_suffix"] == "p4a-metrics-test"
    assert payload["local"]["dispatch_success_rate_pct"] == 90.0
    assert payload["skipped"] is False


def test_write_report_includes_shadow_section(tmp_path: Path):
    metrics = {
        "intent_router_shadow": {
            "local": {
                "dispatch_success_rate_pct": 88.0,
                "dispatch_handled": 88,
                "dispatch_total": 100,
                "shadow_regression_mismatch_rate_pct": 0.5,
                "shadow_regression_mismatch": 2,
                "shadow_total": 400,
            }
        }
    }
    meta = {"date": "2026-07-02", "started_at": "t", "elapsed_sec": 1, "use_gpt_user": False, "gpt_scale": False}
    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"
    write_report([], meta, metrics, out_md, out_json)
    text = out_md.read_text(encoding="utf-8")
    assert "IntentRouter Shadow / Dispatch KPI" in text
    assert "dispatch_success_rate_pct" in text
