"""Unit tests for Jev CloudWatch EMF metric derivation (no AWS calls)."""
from __future__ import annotations

from unittest.mock import patch

from src.services import jev_cloudwatch_metrics as jcw


def test_derive_attempt_success_cost():
    inc = jcw.derive_shadow_metric_increments(
        {
            "attempted": True,
            "succeeded": True,
            "mismatch": False,
            "failure_reason": "none",
            "jev_cost_usd_estimate": 0.001,
        }
    )
    assert inc[jcw.METRIC_ATTEMPT] == 1.0
    assert inc[jcw.METRIC_SUCCESS] == 1.0
    assert inc[jcw.METRIC_COST_ESTIMATE] == 0.001
    assert jcw.METRIC_TIMEOUT not in inc


def test_derive_timeout_parse_circuit_queue():
    assert jcw.METRIC_TIMEOUT in jcw.derive_shadow_metric_increments(
        {"attempted": True, "succeeded": False, "failure_reason": "timeout"}
    )
    assert jcw.METRIC_PARSE_FAILURE in jcw.derive_shadow_metric_increments(
        {"attempted": True, "succeeded": False, "error_class": "invalid_schema"}
    )
    assert jcw.METRIC_CIRCUIT_OPEN in jcw.derive_shadow_metric_increments(
        {"attempted": False, "skip_reason": "circuit_open"}
    )
    assert jcw.METRIC_QUEUE_SATURATION in jcw.derive_shadow_metric_increments(
        {"attempted": False, "error_class": "queue_full"}
    )


def test_derive_mismatch_and_high_risk_attempt():
    assert jcw.METRIC_MISMATCH in jcw.derive_shadow_metric_increments(
        {"attempted": True, "succeeded": True, "mismatch": True}
    )
    hr = jcw.derive_shadow_metric_increments(
        {
            "attempted": True,
            "succeeded": False,
            "failure_reason": "high_risk_disagreement",
        }
    )
    assert hr[jcw.METRIC_HIGH_RISK_ATTEMPT] == 1.0


def test_emit_flag_anomaly_only_when_on(monkeypatch):
    emitted: list[dict] = []

    def _capture(metrics, environment=None):
        emitted.append(dict(metrics))

    monkeypatch.setenv("JEV_CW_METRICS", "1")
    monkeypatch.setenv("JEV_D2_ALLOW", "0")
    monkeypatch.setenv("JEV_PRIMARY_ALLOW", "0")
    with patch.object(jcw, "_emit_emf", side_effect=_capture), patch.object(
        jcw, "_emit_put_metric_data"
    ):
        with patch("config.llm_flags.is_jev_intent_router_primary_enabled", return_value=False), patch(
            "config.llm_flags.is_policy_enforcement_d2_enabled", return_value=False
        ):
            jcw.emit_flag_anomaly_metrics()
        assert emitted == []

        with patch("config.llm_flags.is_jev_intent_router_primary_enabled", return_value=True), patch(
            "config.llm_flags.is_policy_enforcement_d2_enabled", return_value=True
        ):
            jcw.emit_flag_anomaly_metrics()
    assert len(emitted) == 1
    assert emitted[0][jcw.METRIC_PRIMARY_FLAG_ANOMALY] == 1.0
    assert emitted[0][jcw.METRIC_D2_FLAG_ANOMALY] == 1.0


def test_d2_allow_suppresses_anomaly(monkeypatch):
    emitted: list[dict] = []
    monkeypatch.setenv("JEV_CW_METRICS", "1")
    monkeypatch.setenv("JEV_D2_ALLOW", "1")
    with patch.object(jcw, "_emit_emf", side_effect=lambda m, environment=None: emitted.append(dict(m))), patch.object(
        jcw, "_emit_put_metric_data"
    ), patch("config.llm_flags.is_jev_intent_router_primary_enabled", return_value=False), patch(
        "config.llm_flags.is_policy_enforcement_d2_enabled", return_value=True
    ):
        jcw.emit_flag_anomaly_metrics()
    assert emitted == []


def test_primary_allow_suppresses_anomaly(monkeypatch):
    emitted: list[dict] = []
    monkeypatch.setenv("JEV_CW_METRICS", "1")
    monkeypatch.setenv("JEV_PRIMARY_ALLOW", "1")
    with patch.object(jcw, "_emit_emf", side_effect=lambda m, environment=None: emitted.append(dict(m))), patch.object(
        jcw, "_emit_put_metric_data"
    ), patch("config.llm_flags.is_jev_intent_router_primary_enabled", return_value=True), patch(
        "config.llm_flags.is_policy_enforcement_d2_enabled", return_value=False
    ):
        jcw.emit_flag_anomaly_metrics()
    assert emitted == []


def test_emf_payload_has_safe_dimensions_only():
    payload = jcw._build_emf_payload({jcw.METRIC_ATTEMPT: 1.0}, environment="staging")
    assert payload["Environment"] == "staging"
    assert payload["Service"] == "medicine-recommend"
    assert payload["_aws"]["CloudWatchMetrics"][0]["Namespace"] == jcw.NAMESPACE
    # No free-text / PII keys
    forbidden = {"user_input", "sid", "answers", "prompt", "api_key"}
    assert not (forbidden & set(payload.keys()))
