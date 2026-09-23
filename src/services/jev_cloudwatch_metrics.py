"""Jev shadow → CloudWatch metrics (EMF), PII-safe.

Emits **names-only counters / estimates** via Embedded Metric Format on stdout
(awslogs → CloudWatch Logs auto-extract). Never includes user text, SID,
answers, prompts, or secret values.

Kill switch: ``JEV_CW_METRICS=0`` disables emit.
Optional PutMetricData path: ``JEV_CW_PUT_METRIC=1`` (requires IAM).
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)
# Dedicated logger: JSON EMF lines only (INFO). Root handlers → container stdout.
_emf_logger = logging.getLogger("jev.cw_emf")

NAMESPACE = "MedicineRecommend/Jev"
SERVICE_DIM = "medicine-recommend"

# Metric names (R21 contract — no payload dimensions beyond Environment/Service)
METRIC_ATTEMPT = "attempt"
METRIC_SUCCESS = "success"
METRIC_TIMEOUT = "timeout"
METRIC_PARSE_FAILURE = "parse_failure"
METRIC_FALLBACK = "fallback"
METRIC_MISMATCH = "mismatch"
METRIC_CIRCUIT_OPEN = "circuit_open"
METRIC_QUEUE_SATURATION = "queue_saturation"
METRIC_HIGH_RISK_ATTEMPT = "high_risk_attempt"
METRIC_COST_ESTIMATE = "cost_estimate"
METRIC_PRIMARY_FLAG_ANOMALY = "primary_flag_anomaly"
METRIC_D2_FLAG_ANOMALY = "D2_flag_anomaly"

_PARSE_FAILURE_REASONS = frozenset(
    {"invalid_schema", "invalid_json", "schema_error"}
)
_CIRCUIT_REASONS = frozenset(
    {"circuit_open", "circuit_open_manual", "circuit_half_open_saturated"}
)
_QUEUE_REASONS = frozenset({"queue_full"})
_TIMEOUT_REASONS = frozenset({"timeout", "TimeoutError"})


def _env_flag_true(name: str, default: str = "1") -> bool:
    raw = (os.getenv(name, default) or default).strip().lower()
    return raw not in ("0", "false", "off", "no")


def _resolve_environment() -> str:
    for key in ("APP_ENV", "ENVIRONMENT", "ENV"):
        raw = (os.getenv(key) or "").strip()
        if raw:
            return raw.lower()[:32]
    return "unknown"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def derive_shadow_metric_increments(event: Mapping[str, Any]) -> dict[str, float]:
    """Map a scrubbed shadow event to metric name → numeric increment.

    Only numeric aggregates; never copies event text fields.
    """
    out: dict[str, float] = {}
    attempted = bool(event.get("attempted"))
    succeeded = bool(event.get("succeeded"))
    failure = str(event.get("failure_reason") or "")
    error = str(event.get("error_class") or "")
    skip = str(event.get("skip_reason") or "")
    fallback = str(event.get("fallback_reason") or "")
    reasons = {failure, error, skip}

    if attempted:
        out[METRIC_ATTEMPT] = 1.0
    if succeeded:
        out[METRIC_SUCCESS] = 1.0
    if reasons & _TIMEOUT_REASONS:
        out[METRIC_TIMEOUT] = 1.0
    if reasons & _PARSE_FAILURE_REASONS:
        out[METRIC_PARSE_FAILURE] = 1.0
    if attempted and fallback and fallback not in ("none", "not_eligible", ""):
        out[METRIC_FALLBACK] = 1.0
    elif attempted and not succeeded and failure not in ("none", ""):
        out[METRIC_FALLBACK] = 1.0
    if bool(event.get("mismatch")):
        out[METRIC_MISMATCH] = 1.0
    if reasons & _CIRCUIT_REASONS:
        out[METRIC_CIRCUIT_OPEN] = 1.0
    if reasons & _QUEUE_REASONS:
        out[METRIC_QUEUE_SATURATION] = 1.0

    # High-risk API attempt anomaly: attempted while high-risk path / disagreement
    if attempted and (
        failure == "high_risk_disagreement"
        or skip == "deterministic_high_risk"
        or error == "deterministic_high_risk"
    ):
        out[METRIC_HIGH_RISK_ATTEMPT] = 1.0

    cost = None
    cost_block = event.get("cost")
    if isinstance(cost_block, Mapping):
        cost = _safe_float(cost_block.get("jev_cost_usd_estimate"))
    if cost is None:
        cost = _safe_float(event.get("jev_cost_usd_estimate"))
    if cost is not None and cost >= 0:
        out[METRIC_COST_ESTIMATE] = float(cost)

    return out


def _build_emf_payload(
    metrics: Mapping[str, float],
    *,
    environment: Optional[str] = None,
) -> dict[str, Any]:
    env = (environment or _resolve_environment())[:32]
    metric_defs = []
    body: dict[str, Any] = {
        "Environment": env,
        "Service": SERVICE_DIM,
    }
    for name, value in metrics.items():
        unit = "None" if name == METRIC_COST_ESTIMATE else "Count"
        metric_defs.append({"Name": name, "Unit": unit})
        body[name] = float(value)
    body["_aws"] = {
        "Timestamp": int(time.time() * 1000),
        "CloudWatchMetrics": [
            {
                "Namespace": NAMESPACE,
                "Dimensions": [["Environment", "Service"]],
                "Metrics": metric_defs,
            }
        ],
    }
    return body


def _emit_emf(metrics: Mapping[str, float], *, environment: Optional[str] = None) -> None:
    if not metrics:
        return
    if not _env_flag_true("JEV_CW_METRICS", "1"):
        return
    payload = _build_emf_payload(metrics, environment=environment)
    # Single-line JSON only — no extra fields that could carry PII.
    _emf_logger.info("%s", json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


def _emit_put_metric_data(
    metrics: Mapping[str, float],
    *,
    environment: Optional[str] = None,
) -> None:
    """Optional boto3 PutMetricData (off by default). Failures never raise."""
    if not metrics or not _env_flag_true("JEV_CW_PUT_METRIC", "0"):
        return
    try:
        import boto3

        env = (environment or _resolve_environment())[:32]
        region = (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-1").strip()
        client = boto3.client("cloudwatch", region_name=region)
        dims = [
            {"Name": "Environment", "Value": env},
            {"Name": "Service", "Value": SERVICE_DIM},
        ]
        # CloudWatch allows max 1000 metrics / 20 per call; we send << 20.
        metric_data = []
        for name, value in metrics.items():
            unit = "None" if name == METRIC_COST_ESTIMATE else "Count"
            metric_data.append(
                {
                    "MetricName": name,
                    "Dimensions": dims,
                    "Value": float(value),
                    "Unit": unit,
                }
            )
        client.put_metric_data(Namespace=NAMESPACE, MetricData=metric_data)
    except Exception:
        logger.debug("jev cw put_metric_data failed", exc_info=True)


def emit_shadow_cloudwatch_metrics(event: Mapping[str, Any]) -> None:
    """Derive + emit CW metrics from a shadow event dict. Never raises."""
    try:
        if not isinstance(event, Mapping):
            return
        increments = derive_shadow_metric_increments(event)
        env = None
        raw_env = event.get("environment")
        if isinstance(raw_env, str) and raw_env.strip():
            env = raw_env.strip().lower()[:32]
        _emit_emf(increments, environment=env)
        _emit_put_metric_data(increments, environment=env)
    except Exception:
        logger.debug("jev emit_shadow_cloudwatch_metrics failed", exc_info=True)


def emit_flag_anomaly_metrics() -> None:
    """Emit PRIMARY / D2 anomaly gauges only when unexpectedly ON.

    ``D2_flag_anomaly`` fires when D2 is ON and ``JEV_D2_ALLOW`` is not truthy
    (canary allow-list). Failures never raise.
    """
    try:
        if not _env_flag_true("JEV_CW_METRICS", "1"):
            return
        from config.llm_flags import (
            is_jev_intent_router_primary_enabled,
            is_policy_enforcement_d2_enabled,
        )

        metrics: dict[str, float] = {}
        if is_jev_intent_router_primary_enabled():
            metrics[METRIC_PRIMARY_FLAG_ANOMALY] = 1.0
        d2_on = is_policy_enforcement_d2_enabled()
        d2_allowed = _env_flag_true("JEV_D2_ALLOW", "0")
        if d2_on and not d2_allowed:
            metrics[METRIC_D2_FLAG_ANOMALY] = 1.0
        if not metrics:
            return
        _emit_emf(metrics)
        _emit_put_metric_data(metrics)
    except Exception:
        logger.debug("jev emit_flag_anomaly_metrics failed", exc_info=True)


__all__ = [
    "NAMESPACE",
    "METRIC_ATTEMPT",
    "METRIC_SUCCESS",
    "METRIC_TIMEOUT",
    "METRIC_PARSE_FAILURE",
    "METRIC_FALLBACK",
    "METRIC_MISMATCH",
    "METRIC_CIRCUIT_OPEN",
    "METRIC_QUEUE_SATURATION",
    "METRIC_HIGH_RISK_ATTEMPT",
    "METRIC_COST_ESTIMATE",
    "METRIC_PRIMARY_FLAG_ANOMALY",
    "METRIC_D2_FLAG_ANOMALY",
    "derive_shadow_metric_increments",
    "emit_shadow_cloudwatch_metrics",
    "emit_flag_anomaly_metrics",
]
