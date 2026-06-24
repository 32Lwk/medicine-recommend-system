"""
GCP ログ解析の品質メトリクス集計。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict


def build_quality_metrics(bundle: Dict[str, Any]) -> Dict[str, Any]:
    sections = bundle.get("sections") or {}
    user_sessions = sections.get("user_sessions") or {}
    sc = user_sessions.get("session_conversations") or {}
    errors = sections.get("errors_http") or {}

    issue_totals: Counter[str] = Counter()
    severity_totals: Counter[str] = Counter()
    for mismatch in sc.get("intent_mismatches") or []:
        issue_totals[mismatch.get("issue_type") or "unknown"] += 1
        severity_totals[mismatch.get("severity") or "info"] += 1

    physical_sessions = sum(
        1
        for s in sc.get("sessions") or []
        if (s.get("physical_recommendation_summary") or {}).get("physical_turn_count", 0) > 0
    )
    medicine_events = len(sc.get("physical_recommendation_events") or [])

    http = errors.get("http") or {}
    return {
        "conversation": {
            "session_count": sc.get("session_count", 0),
            "exported_session_count": sc.get("exported_session_count", 0),
            "sessions_by_grade": sc.get("sessions_by_grade") or {},
            "heuristic_mismatch_count": sc.get("mismatch_count", 0),
            "heuristic_issue_types": dict(issue_totals),
            "heuristic_severity": dict(severity_totals),
            "physical_sessions_with_advisor_hook": physical_sessions,
            "physical_recommendation_log_events": medicine_events,
            "counseling_detail_count": user_sessions.get("counseling_detail_count", 0),
            "counseling_after_dedup": user_sessions.get("counseling_details_exported", 0),
        },
        "infra": {
            "http_4xx_5xx_total": http.get("http_4xx_5xx_total", 0),
            "http_by_status": http.get("by_status") or {},
        },
        "llm_review_note": (
            "heuristic_* は LLM 最終判定の参考シグナル。Skill 実行時に conversation_history を読み全ターン再評価すること。"
        ),
    }
