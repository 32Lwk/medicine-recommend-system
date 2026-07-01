"""IntentRouter shadow / dispatch ログ集計（Wave 1b 観測性）。"""
from __future__ import annotations

from collections import Counter
from typing import Any


def measure_intent_router_logs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """dialogue_route_shadow / dialogue_route_dispatch JSONL 行を集計。"""
    shadow = [r for r in rows if r.get("log_type") == "dialogue_route_shadow"]
    dispatch = [r for r in rows if r.get("log_type") == "dialogue_route_dispatch"]

    shadow_mismatch = sum(1 for r in shadow if r.get("mismatch"))
    dispatch_handled = sum(1 for r in dispatch if r.get("handled"))
    dispatch_missed = sum(1 for r in dispatch if r.get("handled") is False)

    shadow_by_route = dict(Counter(str(r.get("primary_route") or "unknown") for r in shadow))
    shadow_by_resolved = dict(Counter(str(r.get("resolved_by") or "unknown") for r in shadow))
    dispatch_by_handler = dict(Counter(str(r.get("handler") or "unknown") for r in dispatch))

    mismatch_rate = (shadow_mismatch / len(shadow) * 100) if shadow else 0.0
    dispatch_success_rate = (dispatch_handled / len(dispatch) * 100) if dispatch else 0.0

    samples_mismatch = [
        {
            "session_id": r.get("session_id"),
            "user_input": (r.get("user_input") or "")[:80],
            "primary_route": r.get("primary_route"),
            "triage_category": r.get("triage_category"),
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
        "shadow_mismatch_rate_pct": round(mismatch_rate, 2),
        "shadow_by_primary_route": shadow_by_route,
        "shadow_by_resolved_by": shadow_by_resolved,
        "shadow_with_fever_context_flag": shadow_with_fever_flag,
        "shadow_with_pending_cancelled_flag": shadow_with_pending_cancel,
        "dispatch_with_fever_context_flag": dispatch_with_fever_flag,
        "dispatch_with_pending_cancelled_flag": dispatch_with_pending_cancel,
        "dispatch_total": len(dispatch),
        "dispatch_handled": dispatch_handled,
        "dispatch_unhandled": dispatch_missed,
        "dispatch_success_rate_pct": round(dispatch_success_rate, 2),
        "dispatch_by_handler": dispatch_by_handler,
        "mismatch_samples": samples_mismatch,
    }


def merge_log_rows(*row_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for rows in row_lists:
        merged.extend(rows)
    return merged
