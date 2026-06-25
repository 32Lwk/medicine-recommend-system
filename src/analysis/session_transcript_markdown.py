"""
セッション会話の Markdown トランスクリプト生成（送受信時刻・処理時間付き）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def safe_session_filename(session_id: str) -> str:
    safe = str(session_id).replace(":", "_").replace("/", "_").replace("\\", "_")
    return safe[:80]


def summarize_pipeline_breakdown(breakdown: Dict[str, Any]) -> Dict[str, Optional[float]]:
    if not breakdown:
        return {}

    def span(start_key: str, end_key: str) -> Optional[float]:
        if start_key in breakdown and end_key in breakdown:
            return round(float(breakdown[end_key]) - float(breakdown[start_key]), 1)
        return None

    return {
        "security_ms": span("before_security", "after_security"),
        "triage_ms": span("before_triage", "after_triage"),
        "post_to_security_ms": span("post_start", "after_security"),
        "safety_gate_ms": span("after_security", "safety_gate_done"),
        "confidence_gate_ms": span("safety_gate_done", "confidence_gate_done"),
        "orchestrator_ms": span("before_orchestrator", "orch_route_end"),
        "concierge_build_ms": span("concierge_build_payload_start", "concierge_build_payload_end"),
        "meta_triage_ms": span("meta_triage_start", "meta_triage_end"),
    }


def build_turn_timing(
    *,
    trace: Optional[Dict[str, Any]],
    response_at: str,
    previous_response_at: Optional[str] = None,
) -> Dict[str, Any]:
    perf = (trace or {}).get("pipeline_perf") or {}
    breakdown = perf.get("breakdown") or {}
    llm = perf.get("llm") or {}
    started_at = (trace or {}).get("started_at")

    e2e_ms: Optional[float] = None
    if started_at and response_at:
        from src.analysis.session_conversation_analysis import _parse_ts

        t0, t1 = _parse_ts(started_at), _parse_ts(response_at)
        if t0 and t1:
            delta = (t1 - t0).total_seconds() * 1000
            if delta >= 0:
                e2e_ms = round(delta, 1)
            elif perf.get("total_ms") is not None:
                e2e_ms = round(float(perf["total_ms"]), 1)

    since_prev: Optional[float] = None
    if previous_response_at and response_at:
        from src.analysis.session_conversation_analysis import _parse_ts

        t0, t1 = _parse_ts(previous_response_at), _parse_ts(response_at)
        if t0 and t1:
            since_prev = round((t1 - t0).total_seconds() * 1000, 1)

    phase_summary = summarize_pipeline_breakdown(breakdown)
    llm_calls = llm.get("llm_calls") or []

    return {
        "user_message_at": started_at,
        "response_at": response_at,
        "e2e_ms": e2e_ms,
        "since_previous_turn_ms": since_prev,
        "pipeline_total_ms": perf.get("total_ms"),
        "phase_summary_ms": phase_summary,
        "breakdown_ms": breakdown,
        "llm_call_count": llm.get("llm_call_count") or len(llm_calls),
        "llm_total_latency_ms": llm.get("llm_total_latency_ms"),
        "llm_session_cost_jpy": llm.get("llm_session_cost_jpy"),
        "llm_calls": llm_calls,
    }


def enrich_routing_from_trace(trace: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """_routing_from_trace の拡張版（breakdown / llm を含む）。"""
    if not trace:
        return {}
    handoff_target = None
    concierge_handled = None
    concierge_ms = None
    for step in trace.get("agent_steps") or []:
        payload = step.get("payload") or {}
        if step.get("agent") == "ChatOrchestrator" and step.get("step") == "handoff":
            handoff_target = payload.get("target")
        if step.get("agent") == "ConciergeAgent" and step.get("step") == "complete":
            concierge_handled = payload.get("handled")
            concierge_ms = step.get("ms")
    perf = trace.get("pipeline_perf") or {}
    return {
        "trace_id": trace.get("trace_id"),
        "triage": trace.get("triage"),
        "concierge_intent": trace.get("concierge_intent"),
        "structural_intent": trace.get("structural_intent"),
        "meta_intent": trace.get("meta_intent"),
        "handoff_target": handoff_target,
        "concierge_handled": concierge_handled,
        "concierge_ms": concierge_ms,
        "total_ms": perf.get("total_ms"),
        "channel": perf.get("channel"),
        "phase_summary_ms": summarize_pipeline_breakdown(perf.get("breakdown") or {}),
        "llm_call_count": (perf.get("llm") or {}).get("llm_call_count"),
    }


def _fmt_ms(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.0f} ms"
    except (TypeError, ValueError):
        return str(value)


def _fmt_ts(value: Any) -> str:
    if not value:
        return "—"
    return str(value).replace("T", " ").rstrip("Z")


def _truncate(text: str, limit: int = 280) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def render_turn_detail_block(turn: Dict[str, Any], index: int) -> List[str]:
    timing = turn.get("timing") or {}
    routing = turn.get("routing") or {}
    phases = timing.get("phase_summary_ms") or {}
    lines = [
        f"### ターン {index}",
        "",
        "| 項目 | 値 |",
        "|------|-----|",
        f"| ユーザー送信（推定） | `{_fmt_ts(timing.get('user_message_at'))}` |",
        f"| ボット返信（ログ） | `{_fmt_ts(timing.get('response_at'))}` |",
        f"| 前ターン返信からの間隔 | {_fmt_ms(timing.get('since_previous_turn_ms'))} |",
        f"| 受信→返信（E2E） | {_fmt_ms(timing.get('e2e_ms'))} |",
        f"| パイプライン total | {_fmt_ms(timing.get('pipeline_total_ms'))} |",
        f"| trace_id | `{routing.get('trace_id') or '—'}` |",
        "",
        "**ユーザー入力**",
        "",
        "```",
        turn.get("user_input") or "",
        "```",
        "",
        "**ボット返信**",
        "",
        "```",
        _truncate(str(turn.get("response_preview") or ""), 1200),
        "```",
        "",
        "**処理フェーズ（ms・POST 起点の相対）**",
        "",
        "| フェーズ | 時間 |",
        "|---------|------|",
    ]
    for key, label in (
        ("post_to_security_ms", "POST→セキュリティ完了"),
        ("security_ms", "セキュリティ"),
        ("triage_ms", "トリアージ"),
        ("safety_gate_ms", "セーフティゲート"),
        ("confidence_gate_ms", "信頼度ゲート"),
        ("meta_triage_ms", "メタトリアージ"),
        ("orchestrator_ms", "オーケストレーター"),
        ("concierge_build_ms", "Concierge 応答生成"),
    ):
        val = phases.get(key)
        if val is not None:
            lines.append(f"| {label} | {val:,.1f} ms |")
    if not any(phases.get(k) is not None for k, _ in (
        ("post_to_security_ms", ""), ("security_ms", ""), ("triage_ms", ""),
    )):
        lines.append("| （breakdown なし） | — |")

    llm_calls = timing.get("llm_calls") or []
    if llm_calls:
        lines.extend(["", "**LLM 呼び出し**", "", "| path | model | latency | cost (JPY) |", "|------|-------|---------|------------|"])
        for call in llm_calls:
            lines.append(
                f"| {call.get('path', '—')} | {call.get('model', '—')} | "
                f"{_fmt_ms(call.get('latency_ms'))} | {call.get('cost_jpy', '—')} |"
            )
    lines.append("")
    return lines


def render_session_transcript_markdown(session: Dict[str, Any]) -> str:
    sid = session.get("session_id") or "unknown"
    evaluation = session.get("evaluation") or {}
    turns = session.get("turns") or []
    time_range = session.get("time_range") or {}

    lines = [
        f"# セッション transcript: `{sid}`",
        "",
        "| 項目 | 値 |",
        "|------|-----|",
        f"| channel | {session.get('channel', '—')} |",
        f"| 期間 | `{_fmt_ts(time_range.get('start'))}` ～ `{_fmt_ts(time_range.get('end'))}` |",
        f"| ターン数 | {len(turns)} |",
        f"| heuristic grade | {evaluation.get('overall_grade', '—')} |",
        "",
        "## 会話一覧（時系列）",
        "",
        "| # | ユーザー送信（推定） | ボット返信時刻 | ユーザー入力 | ボット返信（抜粋） | E2E | pipeline | 前ターン間隔 |",
        "|---|---------------------|----------------|--------------|-------------------|-----|----------|--------------|",
    ]
    for i, turn in enumerate(turns, 1):
        timing = turn.get("timing") or {}
        lines.append(
            f"| {i} | `{_fmt_ts(timing.get('user_message_at'))}` | `{_fmt_ts(timing.get('response_at'))}` | "
            f"{_truncate(str(turn.get('user_input') or ''), 40)} | "
            f"{_truncate(str(turn.get('response_preview') or ''), 50)} | "
            f"{_fmt_ms(timing.get('e2e_ms'))} | {_fmt_ms(timing.get('pipeline_total_ms'))} | "
            f"{_fmt_ms(timing.get('since_previous_turn_ms'))} |"
        )

    lines.extend(["", "## ターン別詳細（送受信・処理時間）", ""])
    for i, turn in enumerate(turns, 1):
        lines.extend(render_turn_detail_block(turn, i))

    return "\n".join(lines).rstrip() + "\n"


def write_session_transcripts(
    session_data: Dict[str, Any],
    output_dir: Any,
) -> Dict[str, str]:
    """log/analysis/<stem>/sessions/<safe_id>.md を書き出す。"""
    from pathlib import Path

    out = Path(output_dir)
    sessions_dir = out / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    for session in session_data.get("sessions") or []:
        sid = session.get("session_id") or "unknown"
        fname = f"{safe_session_filename(sid)}.md"
        path = sessions_dir / fname
        path.write_text(render_session_transcript_markdown(session), encoding="utf-8")
        paths[str(sid)] = str(path)
    return paths
