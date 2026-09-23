"""Jev IntentRouter shadow 観測メトリクス（Phase 1B / Agent D Observability）。

書き込み失敗は本線へ伝播させない。生テキスト・SID・API key は記録しない。

コスト命名規則（厳守）:
- ``*_estimate`` / ``*_estimated`` … 単価×token 等からの**推定**。実測と呼ぶな。
- ``*_actual`` … API/課金ログ等から得た**実測**（未取得時は null）。
- **新規集計は ``jev_cost_usd_estimate`` のみ推奨。**
- ``jev_cost_usd`` は **DEPRECATED** 互換エイリアス（中身は常に ``jev_cost_usd_estimate`` と同じ推定値）。
  即削除は破壊的なため維持するが、実測と呼ぶな・新規ダッシュボードに使うな。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2
LOG_FILE = "jev_intent_router_shadow.jsonl"
LOG_TYPE = "jev_intent_router_shadow"
ADAPTER_MODE = "minimal"
JEV_INPUT_COST_USD_PER_MTOK = 0.042
_EXECUTION_REGISTRY_MAX = 256

# field_semantics 用。互換トップレベル jev_cost_usd の意味を機械可読で固定する。
JEV_COST_USD_ALIAS_SEMANTICS = "estimated (alias of jev_cost_usd_estimate)"
JEV_COST_USD_DEPRECATION_NOTE = (
    "DEPRECATED: compatibility alias of jev_cost_usd_estimate; "
    "value is estimated (not actual). New aggregations must use "
    "jev_cost_usd_estimate only. Do not delete yet (breaking)."
)

# correlation_id -> executed_decision（dispatcher join 用。失敗は非伝播）
_executed_by_correlation: OrderedDict[str, Any] = OrderedDict()

# --- Event completeness -------------------------------------------------------

REQUIRED_SHADOW_FIELDS: frozenset[str] = frozenset(
    {
        "log_type",
        "schema_version",
        "timestamp",
        "environment",
        "correlation_id",
        "mode",
        "adapter_mode",
        "legacy_decision",
        "jev_decision",
        "executed_decision",
        "matched",
        "disagreement_class",
        "attempted",
        "succeeded",
        "retry_count",
        "fallback_reason",
        "failure_reason",
        "error_class",
        "latency_ms",
        "jev_usage",
        "cost",
    }
)
# event_completeness 自体はメタのため REQUIRED に含めない（自己参照で常に incomplete になる）

# --- Failure reason enum（自由文禁止・未知は other に正規化）-------------------

FAILURE_REASONS: frozenset[str] = frozenset(
    {
        "none",
        "timeout",
        "http_429",
        "http_5xx",
        "http_4xx",
        "network_error",
        "invalid_schema",
        "invalid_json",
        "low_confidence",
        "missing_api_key",
        "queue_full",
        "submit_failed",
        "circuit_open",
        "circuit_open_manual",
        "circuit_half_open_saturated",
        "rate_rpm",
        "rate_rph",
        "rate_rpd",
        "tokens_day",
        "cost_day_estimate",
        "cost_day",
        "emergency_disable",
        "tokens_per_request",
        "unexpected",
        "log_error",
        "recent_context_mismatch",
        "high_risk_disagreement",
        "schema_error",
        "OSError",
        "other",
    }
)

_FAILURE_ALIASES: dict[str, str] = {
    "timeout": "timeout",
    "TimeoutError": "timeout",
    "http_429": "http_429",
    "429": "http_429",
    "http_429_exhausted": "http_429",
    "http_5xx": "http_5xx",
    "http_5xx_exhausted": "http_5xx",
    "http_4xx": "http_4xx",
    "network_error": "network_error",
    "network": "network_error",
    "invalid_schema": "invalid_schema",
    "schema_error": "schema_error",
    "invalid_json": "invalid_json",
    "low_confidence": "low_confidence",
    "missing_api_key": "missing_api_key",
    "queue_full": "queue_full",
    "submit_failed": "submit_failed",
    "circuit_open": "circuit_open",
    "circuit_open_manual": "circuit_open_manual",
    "circuit_half_open_saturated": "circuit_half_open_saturated",
    "rate_rpm": "rate_rpm",
    "rate_rph": "rate_rph",
    "rate_rpd": "rate_rpd",
    "tokens_day": "tokens_day",
    "cost_day_estimate": "cost_day_estimate",
    "cost_day": "cost_day_estimate",
    "emergency_disable": "emergency_disable",
    "tokens_per_request": "tokens_per_request",
    "unexpected": "unexpected",
    "log_error": "log_error",
    "recent_context_mismatch": "recent_context_mismatch",
    "high_risk_disagreement": "high_risk_disagreement",
    "OSError": "OSError",
    "none": "none",
}

# --- PII / secret（assert 禁止・-O でも有効）-----------------------------------

FORBIDDEN_LOG_KEYS: frozenset[str] = frozenset(
    {
        "user_input",
        "user_text",
        "history",
        "recent_turns",
        "recent_context",
        "api_key",
        "authorization",
        "Authorization",
        "cookie",
        "Cookie",
        "raw_answers",
        "answers",
        "baseline_triage_hint",
        "sid",
        "session_id",
        "user_id",
        "line_user_id",
        "user_attributes",
        "email",
        "phone",
        "address",
        "rag",
        "rag_text",
        "system_prompt",
        "generation_prompt",
        "prompt",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "bearer",
    }
)

# API key / Bearer っぽい値。マッチしたら redact（キー名ではなく値検査）。
_SECRET_VALUE_RE = re.compile(
    r"(?i)(?:sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9\-._~+/]+=*|api[_-]?key\s*[:=]\s*\S+)"
)
_REDACTED = "[REDACTED]"


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


# Shadow / eval 比較用の sub-route 別名。実行ルーティングは変更しない。
_EMERGENCY_SUB_ALIASES: dict[str, str] = {
    "chest_pain_breathing_difficulty": "emergency_dispatch",
    "chest_pain_breathlessness": "emergency_dispatch",
    "chest_pain_shortness_of_breath": "emergency_dispatch",
}
_SESSION_SUB_ALIASES: dict[str, str] = {
    "delete_confirm": "delete",
}


def normalize_sub_route(primary: Any, sub: Any) -> Optional[str]:
    """primary 文脈で sub-route 別名を正規化する（比較専用）。

    Emergency の chest_pain_* と SessionOps の delete_confirm は臨床差分ではなく
    naming alias として同一扱いする。実行パスには使わない。
    """
    text = _norm_sub(sub)
    if text is None:
        return None
    primary_key = (_norm_route(primary) or "").lower()
    lowered = text.lower()
    if primary_key == "emergency":
        return _EMERGENCY_SUB_ALIASES.get(lowered, text)
    if primary_key == "sessionops":
        return _SESSION_SUB_ALIASES.get(lowered, text)
    return text


_HIGH_RISK_PRIMARIES = frozenset({"emergency", "security"})
DISAGREEMENT_CLASSES = frozenset(
    {
        "none",
        "primary_route",
        "sub_route",
        "high_risk_signal",
        "execution_effect",
    }
)


def compute_matched(
    legacy_decision: Any,
    jev_decision: Any,
) -> dict[str, bool]:
    """primary / sub / safety / exact の一致フラグ。"""
    legacy = _route_fields(legacy_decision)
    jev = _route_fields(jev_decision) if jev_decision is not None else {}

    primary = _norm_route(legacy.get("primary_route")) == _norm_route(jev.get("primary_route"))
    sub = normalize_sub_route(
        legacy.get("primary_route"), legacy.get("sub_route")
    ) == normalize_sub_route(jev.get("primary_route"), jev.get("sub_route"))

    legacy_primary = (_norm_route(legacy.get("primary_route")) or "").lower()
    jev_primary = (_norm_route(jev.get("primary_route")) or "").lower()
    safety = True
    if legacy_primary in _HIGH_RISK_PRIMARIES or jev_primary in _HIGH_RISK_PRIMARIES:
        safety = legacy_primary == jev_primary

    exact = bool(primary and sub and safety)
    return {
        "primary": bool(primary and jev_decision is not None),
        "sub": bool(sub and jev_decision is not None),
        "safety": bool(safety and jev_decision is not None),
        "exact": exact and jev_decision is not None,
    }


def _routes_equal(a: Any, b: Any) -> bool:
    fa = _route_fields(a)
    fb = _route_fields(b)
    return _norm_route(fa.get("primary_route")) == _norm_route(
        fb.get("primary_route")
    ) and normalize_sub_route(
        fa.get("primary_route"), fa.get("sub_route")
    ) == normalize_sub_route(fb.get("primary_route"), fb.get("sub_route"))


def compute_disagreement_class(
    legacy_decision: Any,
    jev_decision: Any,
    executed_decision: Any = None,
) -> str:
    """差分分類: primary_route / sub_route / high_risk_signal / execution_effect / none。

    優先順位: high_risk_signal > primary_route > sub_route > execution_effect > none。
    jev_decision 欠損時は比較不能のため none。
    """
    if jev_decision is None:
        return "none"

    matched = compute_matched(legacy_decision, jev_decision)
    if not matched["safety"]:
        return "high_risk_signal"
    if not matched["primary"]:
        return "primary_route"
    if not matched["sub"]:
        return "sub_route"

    if executed_decision is not None and not _routes_equal(
        legacy_decision, executed_decision
    ):
        return "execution_effect"
    return "none"


def normalize_failure_reason(
    *,
    succeeded: bool,
    failure_reason: Any = None,
    fallback_reason: Any = None,
    error_class: Any = None,
) -> str:
    """失敗理由を enum に正規化。成功時は ``none``。未知は ``other``（assert なし）。

    候補は failure_reason → fallback_reason → error_class の順。
    未知ラベル（例: ``not_eligible``）はスキップし、後続の既知 enum
    （``queue_full`` / ``submit_failed`` 等）を優先する。
    """
    if succeeded and not failure_reason and not fallback_reason and not error_class:
        return "none"
    saw_unknown = False
    for candidate in (failure_reason, fallback_reason, error_class):
        if candidate is None:
            continue
        text = str(candidate).strip()
        if not text:
            continue
        if text in FAILURE_REASONS:
            return text
        aliased = _FAILURE_ALIASES.get(text) or _FAILURE_ALIASES.get(text.lower())
        if aliased:
            return aliased
        # http_503 等
        lowered = text.lower()
        if lowered.startswith("http_5") or text.startswith("5"):
            return "http_5xx"
        if lowered.startswith("http_4") or text.startswith("4"):
            return "http_4xx"
        saw_unknown = True
        continue
    if succeeded and not saw_unknown:
        return "none"
    return "other"


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
    """Jev 入力コストの**推定**（input $0.042 / MTok）。実測ではない。

    欠損は None（unknown として可視化）。
    """
    try:
        tokens = int(input_tokens)
    except (TypeError, ValueError):
        return None
    if tokens < 0:
        return None
    return round(tokens * JEV_INPUT_COST_USD_PER_MTOK / 1_000_000.0, 10)


def prompt_hash_for_questions(questions: Any, *, model: Optional[str] = None) -> Optional[str]:
    """Stable hash of question schema + model (no user text / PII)."""
    try:
        import json

        blob = json.dumps(
            {"questions": questions, "model": model or ""},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
    except Exception:
        return None


def config_hash_snapshot() -> Optional[str]:
    """Hash of non-secret Jev runtime config (flags + caps). No API keys."""
    try:
        import json

        from config.llm_flags import (
            is_jev_enabled,
            is_jev_intent_router_primary_enabled,
            is_jev_intent_router_shadow_enabled,
            is_policy_enforcement_d2_enabled,
        )
        from config.routing_config import (
            jev_circuit_failure_threshold,
            jev_circuit_half_open_probes,
            jev_circuit_open_sec,
            jev_cost_guard_enabled,
            jev_est_cost_usd_day_max,
            jev_executor_workers,
            jev_http_max_retries,
            jev_max_pending,
            jev_model,
            jev_rate_rpd,
            jev_rate_rph,
            jev_rate_rpm,
            jev_shadow_emergency_disable,
            jev_timeout_sec,
            jev_tokens_day_max,
            jev_tokens_per_request_max,
        )

        snap = {
            "JEV_ENABLED": bool(is_jev_enabled()),
            "JEV_INTENT_ROUTER_SHADOW": bool(is_jev_intent_router_shadow_enabled()),
            "JEV_INTENT_ROUTER_PRIMARY": bool(is_jev_intent_router_primary_enabled()),
            "POLICY_ENFORCEMENT_D2": bool(is_policy_enforcement_d2_enabled()),
            "model": jev_model(),
            "timeout_sec": jev_timeout_sec(),
            "http_max_retries": jev_http_max_retries(),
            "max_pending": jev_max_pending(),
            "workers": jev_executor_workers(),
            "circuit_failure_threshold": jev_circuit_failure_threshold(),
            "circuit_open_sec": jev_circuit_open_sec(),
            "circuit_half_open_probes": jev_circuit_half_open_probes(),
            "rate_rpm": jev_rate_rpm(),
            "rate_rph": jev_rate_rph(),
            "rate_rpd": jev_rate_rpd(),
            "tokens_per_request_max": jev_tokens_per_request_max(),
            "tokens_day_max": jev_tokens_day_max(),
            "est_cost_usd_day_max": jev_est_cost_usd_day_max(),
            "cost_guard_enabled": jev_cost_guard_enabled(),
            "emergency_disable": jev_shadow_emergency_disable(),
        }
        blob = json.dumps(snap, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
    except Exception:
        return None


def redaction_status_from_scrub(
    scrubbed: Any = None,
    remaining: Any = None,
) -> str:
    """ok | scrubbed | remaining_hits — never includes path contents with PII values."""
    rem = list(remaining or [])
    scr = list(scrubbed or [])
    if rem:
        return "remaining_hits"
    if scr:
        return "scrubbed"
    return "ok"


def build_cost_payload(
    *,
    jev_cost_usd_estimate: Optional[float],
    legacy_saved_calls: int,
    openai_cost_usd_actual: Any = None,
    openai_cost_usd_saved_estimate: Any = None,
    openai_cost_jpy_saved_estimate: Any = None,
    cost_basis: Any = None,
    usd_jpy_rate: Any = None,
) -> dict[str, Any]:
    """推定と実測を分離した cost ブロック。

    - ``jev_cost_usd_estimate``: token×単価の**推定**（実測と呼ぶな）。**新規集計の正本**。
    - ``field_semantics['jev_cost_usd']``: トップレベル互換エイリアスの意味
      （``estimated (alias of jev_cost_usd_estimate)``）。値本体は payload トップに残す。
    - ``openai_cost_usd_actual``: OpenAI 側の**実測**（未取得は null）
    - ``openai_cost_*_saved_estimate``: 対照平均等に基づく**推定削減**
    - ``total_classification_cost_usd_estimate``: Jev推定 + OpenAI実測(なければ0加算のみ明示)
    """
    openai_actual = _optional_float(openai_cost_usd_actual)
    openai_saved_usd = _optional_float(openai_cost_usd_saved_estimate)
    openai_saved_jpy = _optional_float(openai_cost_jpy_saved_estimate)
    rate = _optional_float(usd_jpy_rate)

    jev_est = jev_cost_usd_estimate
    # 総分類コスト推定: Jev 推定 + OpenAI 実測（実測欠損時は Jev のみ・フラグで明示）
    total_parts: list[str] = []
    total = 0.0
    total_known = False
    if jev_est is not None:
        total += float(jev_est)
        total_parts.append("jev_cost_usd_estimate")
        total_known = True
    if openai_actual is not None:
        total += float(openai_actual)
        total_parts.append("openai_cost_usd_actual")
        total_known = True

    basis = None
    if isinstance(cost_basis, Mapping):
        basis = {
            k: cost_basis.get(k)
            for k in ("source_log", "path", "avg_cost_jpy", "avg_cost_usd", "calculated_at")
            if k in cost_basis
        }

    return {
        "jev_cost_usd_estimate": jev_est,
        "jev_cost_estimation_basis": (
            f"input_tokens * {JEV_INPUT_COST_USD_PER_MTOK} / 1e6"
            if jev_est is not None
            else None
        ),
        "openai_cost_usd_actual": openai_actual,
        "openai_cost_usd_saved_estimate": openai_saved_usd,
        "openai_cost_jpy_saved_estimate": openai_saved_jpy,
        "usd_jpy_rate": rate,
        "legacy_saved_calls": int(legacy_saved_calls or 0),
        # shadow では二重実行のため削減は通常 0（実測カウント）。推定削減は別フィールド。
        "legacy_saved_calls_measurement": "actual_count",
        "total_classification_cost_usd_estimate": (
            round(total, 10) if total_known else None
        ),
        "total_classification_cost_components": total_parts,
        "cost_basis": basis,
        "field_semantics": {
            "jev_cost_usd_estimate": "estimated",
            # トップレベル互換キー（削除禁止）。推定であり実測ではない。
            "jev_cost_usd": JEV_COST_USD_ALIAS_SEMANTICS,
            "openai_cost_usd_actual": "actual_or_null",
            "openai_cost_usd_saved_estimate": "estimated",
            "openai_cost_jpy_saved_estimate": "estimated",
            "total_classification_cost_usd_estimate": "estimated_sum",
            "legacy_saved_calls": "actual_count",
        },
    }


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def assess_event_completeness(payload: Mapping[str, Any]) -> dict[str, Any]:
    """必須フィールドの有無を評価（assert なし）。"""
    missing = sorted(f for f in REQUIRED_SHADOW_FIELDS if f not in payload)
    # 値が必須で「キーはあるが意味欠損」も軽く見る
    nullish_required: list[str] = []
    for key in (
        "log_type",
        "schema_version",
        "timestamp",
        "mode",
        "adapter_mode",
        "disagreement_class",
        "matched",
        "cost",
        "failure_reason",
    ):
        if key in payload and payload[key] is None:
            nullish_required.append(key)
    complete = not missing and not nullish_required
    return {
        "complete": complete,
        "missing_required": missing,
        "nullish_required": nullish_required,
        "required_field_count": len(REQUIRED_SHADOW_FIELDS),
        "schema_version": SCHEMA_VERSION,
    }


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
    """API から得た token 数（実測）。コスト金額は含めない。"""
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
        "recent_context_count",
        "recent_context_mismatch",
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
        elif key.startswith("has_") or key == "recent_context_mismatch":
            out[key] = bool(value)
        elif key in ("channel",):
            out[key] = str(value) if value is not None else None
        elif key in ("meta_keys", "state_keys") and isinstance(value, (list, tuple)):
            out[key] = [str(v) for v in value][:32]
        else:
            out[key] = value
    return out


def _list_len(value: Any) -> Optional[int]:
    if isinstance(value, list):
        return len(value)
    if value is None:
        return None
    return -1  # present but not a list


def build_state_shape(state: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """送信 state から shape のみ抽出（本文なし）。

    recent_turns（契約）と recent_context（eval alias）の両方を数え、
    長さ不一致を recent_context_mismatch で可視化する。
    """
    if not isinstance(state, Mapping):
        return {}
    recent = state.get("recent_turns")
    recent_ctx = state.get("recent_context")
    has_turns_key = "recent_turns" in state
    has_context_key = "recent_context" in state
    turns_count = _list_len(recent) if has_turns_key else None
    context_count = _list_len(recent_ctx) if has_context_key else None
    if turns_count is None and isinstance(recent, list):
        turns_count = len(recent)
    if turns_count is None:
        turns_count = 0

    mismatch = False
    if has_turns_key and has_context_key:
        if turns_count != context_count:
            mismatch = True
    # 片方欠落は eval/legacy shape でも起きうるため mismatch にはしない。
    # production builder は常に両方を同一 list で埋める。

    meta = state.get("meta") if isinstance(state.get("meta"), Mapping) else {}
    medicines = meta.get("last_recommended_medicines") if isinstance(meta, Mapping) else None
    symptoms = meta.get("active_symptoms") if isinstance(meta, Mapping) else None
    focus = meta.get("medicine_qa_focus") if isinstance(meta, Mapping) else None
    user_input = state.get("user_input")
    shape: dict[str, Any] = {
        "state_keys": sorted(str(k) for k in state.keys()),
        "meta_keys": sorted(str(k) for k in (meta or {}).keys()),
        "recent_turn_count": int(turns_count) if turns_count is not None and turns_count >= 0 else 0,
        "recommended_medicine_count": len(medicines) if isinstance(medicines, list) else 0,
        "has_active_symptoms": bool(symptoms),
        "has_medicine_qa_focus": bool(focus),
        "channel": state.get("channel"),
        "user_input_len": len(str(user_input)) if user_input is not None else 0,
        "recent_context_mismatch": bool(mismatch),
    }
    if context_count is not None and context_count >= 0:
        shape["recent_context_count"] = int(context_count)
    elif has_context_key:
        shape["recent_context_count"] = -1
    return shape


def scrub_forbidden_log_fields(
    payload: MutableMapping[str, Any],
    *,
    path: str = "",
) -> list[str]:
    """禁止キー・秘密値らしき文字列を除去/redact。``assert`` は使わない（-O 耐性）。

    戻り値: 削除または redact したパス一覧。失敗しても例外は外へ出さない想定で
    呼び出し側が try する。
    """
    removed: list[str] = []
    if not isinstance(payload, MutableMapping):
        return removed

    for key in list(payload.keys()):
        key_s = str(key)
        full = f"{path}.{key_s}" if path else key_s
        if key_s in FORBIDDEN_LOG_KEYS or key_s.lower() in FORBIDDEN_LOG_KEYS:
            payload.pop(key, None)
            removed.append(full)
            continue
        value = payload.get(key)
        if isinstance(value, MutableMapping):
            removed.extend(scrub_forbidden_log_fields(value, path=full))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, MutableMapping):
                    removed.extend(
                        scrub_forbidden_log_fields(item, path=f"{full}[{i}]")
                    )
                elif isinstance(item, str) and _SECRET_VALUE_RE.search(item):
                    value[i] = _REDACTED
                    removed.append(f"{full}[{i}]")
        elif isinstance(value, str) and _SECRET_VALUE_RE.search(value):
            payload[key] = _REDACTED
            removed.append(full)
    return removed


def validate_no_forbidden_log_content(payload: Mapping[str, Any]) -> list[str]:
    """混入検査（読み取り専用）。検出パスを返す。raise/assert しない。"""
    hits: list[str] = []

    def _walk(obj: Any, path: str) -> None:
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                key_s = str(k)
                full = f"{path}.{key_s}" if path else key_s
                if key_s in FORBIDDEN_LOG_KEYS or key_s.lower() in FORBIDDEN_LOG_KEYS:
                    hits.append(full)
                _walk(v, full)
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")
        elif isinstance(obj, str) and _SECRET_VALUE_RE.search(obj):
            hits.append(path or "<root>")

    try:
        _walk(payload, "")
    except Exception:
        logger.debug("jev validate_no_forbidden_log_content failed", exc_info=True)
    return hits


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
    failure_reason: Optional[str] = None,
    error_class: Optional[str] = None,
    latency_ms: Optional[float] = None,
    usage: Any = None,
    legacy_saved_calls: int = 0,
    openai_cost_usd_actual: Any = None,
    openai_cost_usd_saved_estimate: Any = None,
    openai_cost_jpy_saved_estimate: Any = None,
    cost_basis: Any = None,
    usd_jpy_rate: Any = None,
    state_shape: Any = None,
    trace_hash: Optional[str] = None,
    sid: Optional[str] = None,
    gate_result: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
    eligible: Optional[bool] = None,
    skip_reason: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    config_hash: Optional[str] = None,
    sre: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """`jev_intent_router_shadow` を JSONL に書く。失敗時は None（例外なし）。"""
    try:
        executed = executed_decision
        if executed is None:
            executed = lookup_executed_decision(correlation_id)
        if executed is None:
            executed = legacy_decision

        usage_payload = _usage_payload(usage)
        jev_cost_estimate = estimate_jev_cost_usd(usage_payload.get("input_tokens"))

        confidence = _extract_confidence_fields(jev_decision)
        matched_payload = dict(matched) if isinstance(matched, Mapping) else compute_matched(
            legacy_decision, jev_decision
        )
        disagreement = compute_disagreement_class(
            legacy_decision, jev_decision, executed_decision=executed
        )

        risk = risk_flags
        if risk is None and jev_decision is not None:
            d = _safe_dict(jev_decision)
            risk = d.get("risk_flags")

        shape_payload = (
            _state_shape_payload(state_shape) if state_shape is not None else None
        )
        effective_error = error_class
        if (
            isinstance(shape_payload, Mapping)
            and shape_payload.get("recent_context_mismatch")
            and not effective_error
        ):
            effective_error = "recent_context_mismatch"
            logger.error(
                "jev state_shape recent_turns/recent_context length mismatch "
                "turns=%s context=%s correlation_id=%s",
                shape_payload.get("recent_turn_count"),
                shape_payload.get("recent_context_count"),
                correlation_id,
            )

        norm_failure = normalize_failure_reason(
            succeeded=bool(succeeded),
            failure_reason=failure_reason,
            fallback_reason=fallback_reason,
            error_class=effective_error or skip_reason,
        )

        jev_usage: Optional[dict[str, Any]] = None
        if usage_payload or model:
            jev_usage = dict(usage_payload)
            if model:
                jev_usage["model"] = model
            # token 数は API usage 由来の実測。金額は入れない。
            jev_usage["token_measurement"] = "actual_usage_or_empty"

        cost_block = build_cost_payload(
            jev_cost_usd_estimate=jev_cost_estimate,
            legacy_saved_calls=int(legacy_saved_calls or 0),
            openai_cost_usd_actual=openai_cost_usd_actual,
            openai_cost_usd_saved_estimate=openai_cost_usd_saved_estimate,
            openai_cost_jpy_saved_estimate=openai_cost_jpy_saved_estimate,
            cost_basis=cost_basis,
            usd_jpy_rate=usd_jpy_rate,
        )

        raw_route = _route_fields(legacy_decision)
        effective_route = _route_fields(jev_decision) if jev_decision is not None else None
        executed_route = _route_fields(executed)

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
            # Naming: raw=legacy, effective=jev shadow parse, executed=production path
            "legacy_decision": raw_route,
            "jev_decision": effective_route,
            "executed_decision": executed_route,
            "raw_decision": raw_route,
            "effective_decision": effective_route,
            "matched": {
                "primary": bool(matched_payload.get("primary")),
                "sub": bool(matched_payload.get("sub")),
                "safety": bool(matched_payload.get("safety")),
                "exact": bool(matched_payload.get("exact")),
            },
            "mismatch": not bool(matched_payload.get("exact")),
            "disagreement_class": disagreement,
            "jev_confidence": confidence or None,
            "risk_flags": risk,
            "eligible": eligible if eligible is not None else bool(attempted),
            "attempted": bool(attempted),
            "succeeded": bool(succeeded),
            "skipped": not bool(attempted),
            "skip_reason": skip_reason or (None if attempted else (effective_error or fallback_reason)),
            "retry_count": int(retry_count or 0),
            "fallback_reason": fallback_reason,
            "failure_reason": norm_failure,
            "error_class": effective_error,
            "latency_ms": latency_ms,
            # 互換: usage は token 実測。jev_usage が正本。
            "usage": usage_payload or None,
            "jev_usage": jev_usage,
            # DEPRECATED 互換エイリアス（即削除禁止）。中身は常に推定。
            # 新規集計・ダッシュボードは jev_cost_usd_estimate のみ推奨。
            "jev_cost_usd": jev_cost_estimate,
            "jev_cost_usd_deprecated": True,
            "jev_cost_usd_deprecation_note": JEV_COST_USD_DEPRECATION_NOTE,
            "jev_cost_usd_estimate": jev_cost_estimate,
            "legacy_saved_calls": int(legacy_saved_calls or 0),
            "cost": cost_block,
            "state_shape": shape_payload,
            "prompt_hash": prompt_hash,
            "config_hash": config_hash if config_hash is not None else config_hash_snapshot(),
            "redaction_status": "ok",
        }
        if isinstance(sre, Mapping):
            payload["sre"] = dict(sre)
        release_id = _resolve_release_id()
        if release_id:
            payload["release_id"] = release_id
        if gate_result is not None:
            payload["gate_result"] = gate_result
        if extra and isinstance(extra, Mapping):
            for k, v in extra.items():
                if k in payload:
                    continue
                if k in FORBIDDEN_LOG_KEYS or str(k).lower() in FORBIDDEN_LOG_KEYS:
                    continue
                payload[k] = v

        # 本番耐性: assert ではなく scrub + error ログ
        scrubbed = scrub_forbidden_log_fields(payload)
        remaining = validate_no_forbidden_log_content(payload)
        payload["redaction_status"] = redaction_status_from_scrub(scrubbed, remaining)
        if scrubbed or remaining:
            logger.error(
                "jev shadow log forbidden/PII scrubbed=%s remaining=%s correlation_id=%s",
                scrubbed,
                remaining,
                correlation_id,
            )
            if remaining and not effective_error:
                payload["error_class"] = "forbidden_log_content"
            payload["pii_scrub"] = {
                "scrubbed_paths": scrubbed,
                "remaining_hits": remaining,
            }

        payload["event_completeness"] = assess_event_completeness(payload)
        if not payload["event_completeness"]["complete"]:
            logger.error(
                "jev shadow event incomplete missing=%s nullish=%s correlation_id=%s",
                payload["event_completeness"].get("missing_required"),
                payload["event_completeness"].get("nullish_required"),
                correlation_id,
            )

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
    "DISAGREEMENT_CLASSES",
    "FAILURE_REASONS",
    "FORBIDDEN_LOG_KEYS",
    "REQUIRED_SHADOW_FIELDS",
    "JEV_INPUT_COST_USD_PER_MTOK",
    "JEV_COST_USD_ALIAS_SEMANTICS",
    "JEV_COST_USD_DEPRECATION_NOTE",
    "assess_event_completeness",
    "build_cost_payload",
    "build_state_shape",
    "clear_execution_registry_for_tests",
    "compute_disagreement_class",
    "compute_matched",
    "config_hash_snapshot",
    "estimate_jev_cost_usd",
    "lookup_executed_decision",
    "normalize_failure_reason",
    "normalize_sub_route",
    "notify_executed_decision",
    "prompt_hash_for_questions",
    "record_shadow_event",
    "redaction_status_from_scrub",
    "scrub_forbidden_log_fields",
    "trace_hash_for_sid",
    "validate_no_forbidden_log_content",
]
