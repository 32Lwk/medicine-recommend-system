"""Jev IntentRouter shadow 観測メトリクス（Phase 1B）。

書き込み失敗は本線へ伝播させない。生テキスト・SID・API key は記録しない。
"""
from __future__ import annotations

import hashlib
import logging
import os
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
LOG_FILE = "jev_intent_router_shadow.jsonl"
LOG_TYPE = "jev_intent_router_shadow"
ADAPTER_MODE = "minimal"
JEV_INPUT_COST_USD_PER_MTOK = 0.042
_EXECUTION_REGISTRY_MAX = 256

# correlation_id -> executed_decision（dispatcher join 用。失敗は非伝播）
_executed_by_correlation: OrderedDict[str, Any] = OrderedDict()


def _safe_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dialogue_routing_dict") and callable(value.to_dialogue_routing_dict):
        try:
            return dict(value.to_dialogue_routing_dict() or {})
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return {
                k: v
                for k, v in vars(value).items()
                if not k.startswith("_") and not callable(v)
            }
        except Exception:
            pass
    return {}


def _route_fields(decision: Any) -> dict[str, Any]:
    d = _safe_dict(decision)
    primary = d.get("primary_route") or d.get("primary")
    sub = d.get("sub_route") if "sub_route" in d else d.get("sub")
    out: dict[str, Any] = {
        "primary_route": primary,
        "sub_route": sub,
    }
    for key in ("confidence", "resolved_by", "source"):
        if key in d and d[key] is not None:
            out[key] = d[key]
    noul = d.get("noul")
    if isinstance(noul, Mapping):
        out["noul"] = dict(noul)
    for key in (
        "primary_confidence",
        "selected_sub_confidence",
        "risk_flags",
        "gate_result",
    ):
        if key in d and d[key] is not None:
            out[key] = d[key]
    return out


def _norm_route(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _norm_sub(value: Any) -> Optional[str]:
    text = _norm_route(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in ("none", "null", "n/a", "-"):
        return None
    return text


def compute_matched(
    legacy_decision: Any,
    jev_decision: Any,
) -> dict[str, bool]:
    """primary / sub / safety / exact の一致フラグ。"""
    legacy = _route_fields(legacy_decision)
    jev = _route_fields(jev_decision) if jev_decision is not None else {}

    primary = _norm_route(legacy.get("primary_route")) == _norm_route(jev.get("primary_route"))
    sub = _norm_sub(legacy.get("sub_route")) == _norm_sub(jev.get("sub_route"))

    legacy_primary = (_norm_route(legacy.get("primary_route")) or "").lower()
    jev_primary = (_norm_route(jev.get("primary_route")) or "").lower()
    high_risk = {"emergency", "security"}
    safety = True
    if legacy_primary in high_risk or jev_primary in high_risk:
        safety = legacy_primary == jev_primary

    exact = bool(primary and sub and safety)
    return {
        "primary": bool(primary and jev_decision is not None),
        "sub": bool(sub and jev_decision is not None),
        "safety": bool(safety and jev_decision is not None),
        "exact": exact and jev_decision is not None,
    }


def trace_hash_for_sid(sid: Optional[str]) -> Optional[str]:
    """SID の一方向ハッシュ。生 sid は返さない。"""
    if not sid:
        return None
    try:
        return hashlib.sha256(str(sid).encode("utf-8")).hexdigest()[:32]
    except Exception:
        return None


def _resolve_environment() -> str:
    for key in ("APP_ENV", "ENVIRONMENT", "ENV"):
        raw = (os.getenv(key) or "").strip()
        if raw:
            return raw.lower()
    return "unknown"


def _resolve_release_id() -> Optional[str]:
    for key in ("RELEASE_ID", "GIT_SHA", "K_REVISION", "COMMIT_SHA"):
        raw = (os.getenv(key) or "").strip()
        if raw:
            return raw[:64]
    return None


def estimate_jev_cost_usd(input_tokens: Any) -> Optional[float]:
    """input $0.042 / MTok。欠損は None（unknown として可視化）。"""
    try:
        tokens = int(input_tokens)
    except (TypeError, ValueError):
        return None
    if tokens < 0:
        return None
    return round(tokens * JEV_INPUT_COST_USD_PER_MTOK / 1_000_000.0, 10)


def notify_executed_decision(
    correlation_id: Optional[str],
    executed_decision: Any,
) -> None:
    """dispatcher が実行 decision を correlation_id で通知する（失敗非伝播）。"""
    try:
        if not correlation_id:
            return
        cid = str(correlation_id)
        _executed_by_correlation[cid] = executed_decision
        _executed_by_correlation.move_to_end(cid)
        while len(_executed_by_correlation) > _EXECUTION_REGISTRY_MAX:
            _executed_by_correlation.popitem(last=False)
    except Exception:
        logger.debug("jev notify_executed_decision failed", exc_info=True)


def lookup_executed_decision(correlation_id: Optional[str]) -> Any:
    if not correlation_id:
        return None
    try:
        return _executed_by_correlation.get(str(correlation_id))
    except Exception:
        return None


def _extract_confidence_fields(jev_decision: Any) -> dict[str, Any]:
    d = _route_fields(jev_decision) if jev_decision is not None else {}
    out: dict[str, Any] = {}
    if "primary_confidence" in d:
        out["primary_confidence"] = d.get("primary_confidence")
    if "selected_sub_confidence" in d:
        out["selected_sub_confidence"] = d.get("selected_sub_confidence")
    if "confidence" in d and "primary_confidence" not in out:
        out["primary_confidence"] = d.get("confidence")
    noul = d.get("noul")
    if isinstance(noul, Mapping):
        out["noul"] = {
            k: noul.get(k)
            for k in (
                "emergency_required",
                "security_risk",
                "store_inquiry",
                "counseling_needed",
            )
            if k in noul
        }
    return out


def _usage_payload(usage: Any) -> dict[str, Any]:
    if not isinstance(usage, Mapping):
        return {}
    out: dict[str, Any] = {}
    for src, dst in (
        ("input_tokens", "input_tokens"),
        ("prompt_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("completion_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        if src in usage and usage[src] is not None and dst not in out:
            try:
                out[dst] = int(usage[src])
            except (TypeError, ValueError):
                out[dst] = usage[src]
    return out


def _state_shape_payload(state_shape: Any) -> dict[str, Any]:
    """keys/lengths only — 生テキスト禁止。"""
    if not isinstance(state_shape, Mapping):
        return {}
    allowed = {
        "recent_turn_count",
        "recommended_medicine_count",
        "has_active_symptoms",
        "has_medicine_qa_focus",
        "channel",
        "user_input_len",
        "meta_keys",
        "state_keys",
    }
    out: dict[str, Any] = {}
    for key, value in state_shape.items():
        if key not in allowed:
            continue
        if key.endswith("_len") or key.endswith("_count"):
            try:
                out[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key.startswith("has_"):
            out[key] = bool(value)
        elif key in ("channel",):
            out[key] = str(value) if value is not None else None
        elif key in ("meta_keys", "state_keys") and isinstance(value, (list, tuple)):
            out[key] = [str(v) for v in value][:32]
        else:
            out[key] = value
    return out


def build_state_shape(state: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """送信 state から shape のみ抽出（本文なし）。"""
    if not isinstance(state, Mapping):
        return {}
    recent = state.get("recent_turns")
    meta = state.get("meta") if isinstance(state.get("meta"), Mapping) else {}
    medicines = meta.get("last_recommended_medicines") if isinstance(meta, Mapping) else None
    symptoms = meta.get("active_symptoms") if isinstance(meta, Mapping) else None
    focus = meta.get("medicine_qa_focus") if isinstance(meta, Mapping) else None
    user_input = state.get("user_input")
    return {
        "state_keys": sorted(str(k) for k in state.keys()),
        "meta_keys": sorted(str(k) for k in (meta or {}).keys()),
        "recent_turn_count": len(recent) if isinstance(recent, list) else 0,
        "recommended_medicine_count": len(medicines) if isinstance(medicines, list) else 0,
        "has_active_symptoms": bool(symptoms),
        "has_medicine_qa_focus": bool(focus),
        "channel": state.get("channel"),
        "user_input_len": len(str(user_input)) if user_input is not None else 0,
    }


def record_shadow_event(
    *,
    correlation_id: Optional[str],
    legacy_decision: Any,
    jev_decision: Any = None,
    executed_decision: Any = None,
    model: Optional[str] = None,
    mode: str = "shadow",
    adapter_mode: str = ADAPTER_MODE,
    matched: Optional[Mapping[str, bool]] = None,
    risk_flags: Any = None,
    attempted: bool = True,
    succeeded: bool = False,
    retry_count: int = 0,
    fallback_reason: Optional[str] = None,
    error_class: Optional[str] = None,
    latency_ms: Optional[float] = None,
    usage: Any = None,
    legacy_saved_calls: int = 0,
    state_shape: Any = None,
    trace_hash: Optional[str] = None,
    sid: Optional[str] = None,
    gate_result: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """`jev_intent_router_shadow` を JSONL に書く。失敗時は None（例外なし）。"""
    try:
        executed = executed_decision
        if executed is None:
            executed = lookup_executed_decision(correlation_id)
        if executed is None:
            executed = legacy_decision

        usage_payload = _usage_payload(usage)
        cost = estimate_jev_cost_usd(usage_payload.get("input_tokens"))

        confidence = _extract_confidence_fields(jev_decision)
        matched_payload = dict(matched) if isinstance(matched, Mapping) else compute_matched(
            legacy_decision, jev_decision
        )

        risk = risk_flags
        if risk is None and jev_decision is not None:
            d = _safe_dict(jev_decision)
            risk = d.get("risk_flags")

        payload: dict[str, Any] = {
            "log_type": LOG_TYPE,
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": _resolve_environment(),
            "correlation_id": str(correlation_id) if correlation_id else None,
            "trace_hash": trace_hash or trace_hash_for_sid(sid),
            "mode": mode,
            "adapter_mode": adapter_mode or ADAPTER_MODE,
            "model": model,
            "legacy_decision": _route_fields(legacy_decision),
            "jev_decision": _route_fields(jev_decision) if jev_decision is not None else None,
            "executed_decision": _route_fields(executed),
            "matched": {
                "primary": bool(matched_payload.get("primary")),
                "sub": bool(matched_payload.get("sub")),
                "safety": bool(matched_payload.get("safety")),
                "exact": bool(matched_payload.get("exact")),
            },
            "jev_confidence": confidence or None,
            "risk_flags": risk,
            "attempted": bool(attempted),
            "succeeded": bool(succeeded),
            "retry_count": int(retry_count or 0),
            "fallback_reason": fallback_reason,
            "error_class": error_class,
            "latency_ms": latency_ms,
            "usage": usage_payload or None,
            "jev_cost_usd": cost,
            "legacy_saved_calls": int(legacy_saved_calls or 0),
            "state_shape": _state_shape_payload(state_shape) if state_shape is not None else None,
        }
        release_id = _resolve_release_id()
        if release_id:
            payload["release_id"] = release_id
        if gate_result is not None:
            payload["gate_result"] = gate_result
        if extra and isinstance(extra, Mapping):
            for k, v in extra.items():
                if k in payload:
                    continue
                # 禁止フィールドを拒否
                if k in (
                    "user_input",
                    "user_text",
                    "history",
                    "recent_turns",
                    "api_key",
                    "authorization",
                    "Authorization",
                    "raw_answers",
                    "answers",
                    "baseline_triage_hint",
                    "sid",
                    "session_id",
                    "user_id",
                ):
                    continue
                payload[k] = v

        _emit_jsonl(payload)
        return payload
    except Exception:
        logger.debug("jev record_shadow_event failed", exc_info=True)
        return None


def _emit_jsonl(data: MutableMapping[str, Any]) -> None:
    try:
        from src.utils.structured_logger import _write_to_jsonl

        _write_to_jsonl(LOG_FILE, dict(data))
    except Exception:
        logger.debug("jev_intent_router_shadow jsonl write failed", exc_info=True)


def clear_execution_registry_for_tests() -> None:
    """テスト専用クリア。"""
    _executed_by_correlation.clear()


__all__ = [
    "SCHEMA_VERSION",
    "LOG_FILE",
    "LOG_TYPE",
    "ADAPTER_MODE",
    "JEV_INPUT_COST_USD_PER_MTOK",
    "build_state_shape",
    "clear_execution_registry_for_tests",
    "compute_matched",
    "estimate_jev_cost_usd",
    "lookup_executed_decision",
    "notify_executed_decision",
    "record_shadow_event",
    "trace_hash_for_sid",
]
