"""IntentRouter shadow / dispatch ログ集計（Wave 1b 観測性）。"""
from __future__ import annotations

from collections import Counter
from typing import Any

from src.dialogue.routing.shadow_mismatch import infer_mismatch_kind_from_log


def _pct(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _safe_log_snippet(text: str, *, limit: int = 80) -> str:
    snippet = (text or "")[:limit]
    return "".join(ch if ch >= " " or ch == "\t" else " " for ch in snippet)


def measure_intent_router_logs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """dialogue_route_shadow / dispatch / execution JSONL 行を集計。"""
    shadow = [r for r in rows if r.get("log_type") == "dialogue_route_shadow"]
    dispatch = [r for r in rows if r.get("log_type") == "dialogue_route_dispatch"]
    execution = [r for r in rows if r.get("log_type") == "dialogue_route_execution"]

    shadow_mismatch = sum(1 for r in shadow if r.get("mismatch"))
    dispatch_handled = sum(1 for r in dispatch if r.get("handled"))
    dispatch_missed = sum(1 for r in dispatch if r.get("handled") is False)

    shadow_kinds = [infer_mismatch_kind_from_log(r) for r in shadow]
    improvement_count = sum(1 for k in shadow_kinds if k == "gate_improvement")
    regression_count = sum(1 for k in shadow_kinds if k == "regression")
    exempt_count = sum(1 for k in shadow_kinds if k == "exempt")

    shadow_by_route = dict(Counter(str(r.get("primary_route") or "unknown") for r in shadow))
    shadow_by_resolved = dict(Counter(str(r.get("resolved_by") or "unknown") for r in shadow))
    shadow_by_mismatch_kind = dict(
        Counter(k or "agree" for k in shadow_kinds)
    )
    dispatch_by_handler = dict(Counter(str(r.get("handler") or "unknown") for r in dispatch))

    execution_mismatch = sum(1 for r in execution if r.get("mismatch"))
    execution_by_layer = dict(Counter(str(r.get("layer_used") or "unknown") for r in execution))
    execution_side_effect = sum(
        1 for r in execution if r.get("dispatch_sub_route") == "medicine_side_effect_qa"
    )

    mismatch_rate = _pct(shadow_mismatch, len(shadow))
    dispatch_success_rate = _pct(dispatch_handled, len(dispatch))

    samples_mismatch = [
        {
            "session_id": r.get("session_id"),
            "user_input": _safe_log_snippet(str(r.get("user_input") or "")),
            "primary_route": r.get("primary_route"),
            "triage_category": r.get("triage_category"),
            "mismatch_kind": infer_mismatch_kind_from_log(r),
            "dialogue_flags": r.get("dialogue_flags"),
        }
        for r in shadow
        if r.get("mismatch")
    ][:20]

    shadow_with_fever_flag = sum(
        1 for r in shadow if (r.get("dialogue_flags") or {}).get("fever_context")
    )
    shadow_with_pending_cancel = sum(
        1
        for r in shadow
        if (r.get("dialogue_flags") or {}).get("pending_cancelled_by_physical")
    )
    dispatch_with_fever_flag = sum(
        1 for r in dispatch if (r.get("dialogue_flags") or {}).get("fever_context")
    )
    dispatch_with_pending_cancel = sum(
        1
        for r in dispatch
        if (r.get("dialogue_flags") or {}).get("pending_cancelled_by_physical")
    )

    return {
        "shadow_total": len(shadow),
        "shadow_mismatch": shadow_mismatch,
        "shadow_mismatch_rate_pct": mismatch_rate,
        "shadow_improvement_mismatch": improvement_count,
        "shadow_improvement_mismatch_rate_pct": _pct(improvement_count, len(shadow)),
        "shadow_regression_mismatch": regression_count,
        "shadow_regression_mismatch_rate_pct": _pct(regression_count, len(shadow)),
        "shadow_exempt": exempt_count,
        "shadow_exempt_rate_pct": _pct(exempt_count, len(shadow)),
        "shadow_by_mismatch_kind": shadow_by_mismatch_kind,
        "shadow_by_primary_route": shadow_by_route,
        "shadow_by_resolved_by": shadow_by_resolved,
        "shadow_with_fever_context_flag": shadow_with_fever_flag,
        "shadow_with_pending_cancelled_flag": shadow_with_pending_cancel,
        "dispatch_with_fever_context_flag": dispatch_with_fever_flag,
        "dispatch_with_pending_cancelled_flag": dispatch_with_pending_cancel,
        "dispatch_total": len(dispatch),
        "dispatch_handled": dispatch_handled,
        "dispatch_unhandled": dispatch_missed,
        "dispatch_success_rate_pct": dispatch_success_rate,
        "dispatch_by_handler": dispatch_by_handler,
        "execution_total": len(execution),
        "execution_mismatch": execution_mismatch,
        "execution_mismatch_rate_pct": _pct(execution_mismatch, len(execution)),
        "execution_by_layer_used": execution_by_layer,
        "execution_side_effect_qa": execution_side_effect,
        "mismatch_samples": samples_mismatch,
    }


def merge_log_rows(*row_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for rows in row_lists:
        merged.extend(rows)
    return merged
