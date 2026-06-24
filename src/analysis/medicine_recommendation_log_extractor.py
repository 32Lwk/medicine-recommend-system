"""
GCP ログから Physical / 薬推奨フロー関連イベントを抽出する。
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from src.analysis.gcp_cloud_run_log_parser import LogEntry

AGENT_STEP_RE = re.compile(r"agent_step\s+(\{.*\})")
PIPELINE_PERF_RE = re.compile(r"PIPELINE_PERF\s+(\{.*\})")
TRACE_ID_RE = re.compile(
    r"trace_id[=:\s\"]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.I,
)

SYMPTOM_DETECT_RE = re.compile(r"症状検出完了:\s*(.+?)(?:\s*\(処理時間|$)")
RECOMMEND_MEDICINES_RE = re.compile(r"推奨医薬品:\s*(.+?)(?:$|処理時間)")
COMPREHENSIVE_START = "包括的医薬品推奨システム開始"


def _safe_literal_eval(blob: str) -> Optional[Dict[str, Any]]:
    try:
        value = ast.literal_eval(blob)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _trace_id_from_text(text: str) -> Optional[str]:
    match = TRACE_ID_RE.search(text)
    return match.group(1) if match else None


def extract_physical_recommendation_events(
    entries: Sequence[LogEntry],
    *,
    max_events: int = 100,
) -> List[Dict[str, Any]]:
    """trace / session に紐づく可能な薬推奨パイプラインイベント。"""
    events: List[Dict[str, Any]] = []
    trace_context: Dict[str, Dict[str, Any]] = {}
    current_trace: Optional[str] = None

    for entry in entries:
        text = entry.text
        trace_id = _trace_id_from_text(text)
        if trace_id:
            current_trace = trace_id
        elif current_trace and ("症状検出" in text or "推奨医薬品" in text or COMPREHENSIVE_START in text):
            trace_id = current_trace
        else:
            step_match = AGENT_STEP_RE.search(text)
            if step_match:
                step = _safe_literal_eval(step_match.group(1))
                if step:
                    trace_id = step.get("trace_id") or current_trace

        session_id = None
        handoff_target = None
        step_match = AGENT_STEP_RE.search(text)
        if step_match:
            step = _safe_literal_eval(step_match.group(1))
            if step:
                session_id = step.get("session_id")
                if step.get("agent") == "ChatOrchestrator" and step.get("step") == "handoff":
                    handoff_target = (step.get("payload") or {}).get("target")

        if trace_id:
            ctx = trace_context.setdefault(trace_id, {"session_id": session_id, "events": []})
            if session_id:
                ctx["session_id"] = session_id

        def push(event_type: str, payload: Dict[str, Any]) -> None:
            if len(events) >= max_events:
                return
            events.append(
                {
                    "timestamp": entry.timestamp,
                    "trace_id": trace_id,
                    "session_id": session_id or (trace_context.get(trace_id or "") or {}).get("session_id"),
                    "event_type": event_type,
                    **payload,
                }
            )

        if COMPREHENSIVE_START in text:
            push("recommendation_pipeline_start", {})
        if handoff_target == "PhysicalHandler":
            push("physical_handoff", {"handoff_target": handoff_target})

        symptom_match = SYMPTOM_DETECT_RE.search(text)
        if symptom_match:
            raw = symptom_match.group(1).strip()
            symptoms = [s.strip() for s in raw.split(",") if s.strip()] if raw != "該当なし" else []
            push("symptoms_detected", {"symptoms": symptoms, "raw": raw[:200]})

        rec_match = RECOMMEND_MEDICINES_RE.search(text)
        if rec_match:
            raw = rec_match.group(1).strip()
            medicines = [m.strip() for m in raw.split(",") if m.strip()] if raw != "該当なし" else []
            push("medicines_recommended", {"medicines": medicines, "raw": raw[:300]})

        perf_match = PIPELINE_PERF_RE.search(text)
        if perf_match and trace_id:
            perf = _safe_literal_eval(perf_match.group(1))
            if perf:
                trace_context.setdefault(trace_id, {})["pipeline_perf"] = perf

    return events


def index_recommendation_events_by_session(
    events: Sequence[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in events:
        sid = event.get("session_id")
        if sid:
            by_session[str(sid)].append(event)
    return dict(by_session)


def attach_physical_recommendation_context(
    session_data: Dict[str, Any],
    recommendation_events: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """session_conversations に Physical 推奨レビュー用コンテキストを付与。"""
    by_session = index_recommendation_events_by_session(recommendation_events)

    for session in session_data.get("sessions") or []:
        sid = session.get("session_id")
        rec_events = by_session.get(str(sid), [])
        physical_turns = []
        for turn in session.get("turns") or []:
            routing = turn.get("routing") or {}
            triage = routing.get("triage") or {}
            is_physical = (
                triage.get("category") == "Physical"
                or routing.get("handoff_target") == "PhysicalHandler"
                or "physical_symptom" in (turn.get("input_labels") or [])
            )
            if not is_physical:
                continue
            turn_events = [
                e
                for e in rec_events
                if e.get("timestamp") and turn.get("timestamp")
                and abs(
                    _ts_key(e["timestamp"]) - _ts_key(turn["timestamp"])
                )
                < 120
            ]
            review = {
                "eligible_for_advisor": True,
                "advisor_skill": "medicine-recommendation-advisor",
                "triage": triage,
                "recommendation_events": turn_events,
                "has_medicine_list": any(e.get("event_type") == "medicines_recommended" for e in turn_events),
            }
            turn["medicine_recommendation_review"] = review
            physical_turns.append(
                {
                    "timestamp": turn.get("timestamp"),
                    "user_input": turn.get("user_input"),
                    "review": review,
                }
            )
        session["physical_recommendation_summary"] = {
            "physical_turn_count": len(physical_turns),
            "recommendation_event_count": len(rec_events),
            "turns": physical_turns,
            "advisor_skill": "medicine-recommendation-advisor",
            "note": "LLM/SKILL 実行時に medicine-recommendation-advisor で上位3品・CSV照合を実施",
        }

    session_data["physical_recommendation_events"] = list(recommendation_events)
    return session_data


def _ts_key(value: str) -> float:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0
