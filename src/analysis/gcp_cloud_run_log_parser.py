"""
GCP Cloud Logging エクスポート JSON（downloaded-logs-*.json）の解析。

巨大ログは決定的に要約・セクション分割し、エージェントの LLM 解析入力に渡す。
"""

from __future__ import annotations

import ast
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from src.analysis.medicine_recommendation_log_extractor import (
    attach_physical_recommendation_context,
    extract_physical_recommendation_events,
)
from src.analysis.quality_metrics import build_quality_metrics
from src.analysis.session_conversation_analysis import (
    build_session_conversations,
    dedupe_counseling_details,
)
from src.analysis.session_transcript_markdown import write_session_transcripts

TRACE_ID_RE = re.compile(
    r"trace_id[=:\s\"]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.I,
)
PIPELINE_PERF_RE = re.compile(r"PIPELINE_PERF\s+(\{.*\})")
AGENT_STEP_RE = re.compile(r"agent_step\s+(\{.*\})")
USER_MESSAGE_RE = re.compile(r"User Message:\s*(.+)")
RECEIVED_MESSAGE_RE = re.compile(r"受信メッセージ:\s*(.+)")
TRIAGE_RESULT_RE = re.compile(
    r"LLMトリアージ結果:\s*([^,]+),\s*subcategory:\s*([^,]+),\s*confidence:\s*([\d.]+)"
)
CONCIERGE_INTENT_RE = re.compile(r"ConciergeAgent:\s*intent=(\w+)")
STRUCTURAL_INTENT_RE = re.compile(r"structural intent=(\w+)")
META_INTENT_RE = re.compile(r"meta intent=(\w+)")
JSON_LOG_START = "{"
JSON_LOG_END = "}"

DB_KEYWORDS = (
    "neon",
    "database",
    "connection",
    "psycopg",
    "sqlalchemy",
    "get_session_from_db",
    "persist_session",
    "db reconnect",
    "operationalerror",
    "timeout",
    "database unavailable",
)
LINE_LOCK_KEYWORDS = (
    "job lock",
    "linejoblock",
    "skipping duplicate",
    "waiting for",
    "acquire",
    "inflight",
)
ERROR_NOISE = (
    "worker (pid:",
    "was sent sigterm",
)


@dataclass
class LogEntry:
    timestamp: str
    severity: str
    text: str
    http: Optional[Dict[str, Any]] = None
    labels: Dict[str, str] = field(default_factory=dict)
    resource: Dict[str, Any] = field(default_factory=dict)
    log_name: str = ""
    trace: str = ""
    insert_id: str = ""

    @classmethod
    def from_gcp(cls, raw: Dict[str, Any]) -> "LogEntry":
        return cls(
            timestamp=raw.get("timestamp", ""),
            severity=raw.get("severity", "DEFAULT"),
            text=raw.get("textPayload", "") or "",
            http=raw.get("httpRequest"),
            labels=dict(raw.get("labels") or {}),
            resource=dict(raw.get("resource") or {}),
            log_name=raw.get("logName", ""),
            trace=raw.get("trace", ""),
            insert_id=raw.get("insertId", ""),
        )


def load_gcp_log_entries(path: Path) -> List[LogEntry]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    return [LogEntry.from_gcp(item) for item in data]


DEV_MD_HEADER_RE = re.compile(r"^# Development log (?P<date>\d{4}-\d{2}-\d{2})\s*$")
DEV_MD_BULLET_RE = re.compile(
    r"^- `(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})` \*\*(?P<level>\w+)\*\* `(?P<logger>[^`]+)`: (?P<message>.*)$"
)


def load_dev_markdown_log_entries(path: Path) -> List[LogEntry]:
    """log/log/yyyy-mm-dd-n.md（開発日次 Markdown）を LogEntry 列に変換する。"""
    entries: List[LogEntry] = []
    current_date: Optional[str] = None
    with path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line or line.startswith("  <details>") or line.startswith("</details>"):
                continue
            header = DEV_MD_HEADER_RE.match(line)
            if header:
                current_date = header.group("date")
                continue
            bullet = DEV_MD_BULLET_RE.match(line)
            if bullet:
                day = current_date or "1970-01-01"
                ts = f"{day}T{bullet.group('time')}"
                entries.append(
                    LogEntry(
                        timestamp=ts,
                        severity=bullet.group("level"),
                        text=bullet.group("message"),
                        labels={"logger": bullet.group("logger"), "environment": "local-dev"},
                    )
                )
                continue
            stripped = line.strip()
            if stripped.startswith(JSON_LOG_START):
                prev_ts = entries[-1].timestamp if entries else ""
                entries.append(
                    LogEntry(
                        timestamp=prev_ts,
                        severity="INFO",
                        text=stripped,
                        labels={"environment": "local-dev"},
                    )
                )
    return entries


def _parse_latency_seconds(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        return float(str(value).replace("s", ""))
    except ValueError:
        return None


def _stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None, "median": None, "p95": None}
    sorted_v = sorted(values)
    n = len(sorted_v)

    def pct(p: float) -> float:
        idx = min(n - 1, max(0, int(round((n - 1) * p))))
        return sorted_v[idx]

    return {
        "count": n,
        "min": round(sorted_v[0], 3),
        "max": round(sorted_v[-1], 3),
        "avg": round(statistics.mean(sorted_v), 3),
        "median": round(statistics.median(sorted_v), 3),
        "p95": round(pct(0.95), 3),
    }


def _service_name(entry: LogEntry) -> str:
    labels = entry.resource.get("labels") or {}
    return str(labels.get("service_name") or "unknown")


def _request_path(url: str) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).path or "/"
    except Exception:
        return url


def _safe_literal_eval(blob: str) -> Optional[Dict[str, Any]]:
    try:
        value = ast.literal_eval(blob)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _json_brace_depth_delta(text: str) -> int:
    """JSON 文字列リテラル外の `{` / `}` だけを数え、深さの増減を返す。"""
    delta = 0
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            delta += 1
        elif ch == "}":
            delta -= 1
    return delta


def _try_parse_json_dict(blob: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _extract_json_from_log_line(stripped: str) -> Optional[Dict[str, Any]]:
    """1 行ログ（compact JSON またはログ接頭辞付き）から dict を取り出す。"""
    start = stripped.find(JSON_LOG_START)
    if start < 0:
        return None
    return _try_parse_json_dict(stripped[start:])


def _extract_multiline_json_objects(entries: Sequence[LogEntry]) -> List[Dict[str, Any]]:
    """structured_logger が行分割した JSON ブロックを再構成する。

    旧実装は行単位の ``}`` でブロック終了とみなしていたため、
    ``conversation_history`` 内のネスト ``{`` / ``}`` で途中分割されていた。
    brace depth を追跡し、トップレベルが閉じた時点で ``json.loads`` する。
    compact 1 行 JSON（``structured_logger`` 現行出力）も同関数で拾う。
    """
    objects: List[Dict[str, Any]] = []
    buffer: List[str] = []
    depth = 0

    for entry in entries:
        stripped = entry.text.rstrip("\n").strip()
        if not stripped:
            continue

        if depth == 0:
            inline = _extract_json_from_log_line(stripped)
            if inline is not None:
                objects.append(inline)
                continue
            if stripped == JSON_LOG_START:
                buffer = [stripped]
                depth = 1
            continue

        buffer.append(stripped)
        depth += _json_brace_depth_delta(stripped)
        if depth <= 0:
            obj = _try_parse_json_dict("\n".join(buffer))
            if obj is not None:
                objects.append(obj)
            buffer = []
            depth = 0

    return objects


def extract_metadata(entries: Sequence[LogEntry], source_path: Path) -> Dict[str, Any]:
    services = Counter(
        name for name in (_service_name(e) for e in entries) if name != "unknown"
    )
    revisions = Counter()
    commits = Counter()
    severities = Counter(e.severity for e in entries if e.severity)
    timestamps = [e.timestamp for e in entries if e.timestamp]

    for entry in entries:
        res_labels = entry.resource.get("labels") or {}
        if res_labels.get("revision_name"):
            revisions[res_labels["revision_name"]] += 1
        if entry.labels.get("commit-sha"):
            commits[entry.labels["commit-sha"]] += 1

    return {
        "source_path": str(source_path),
        "source_name": source_path.name,
        "entry_count": len(entries),
        "time_range": {
            "start": min(timestamps) if timestamps else None,
            "end": max(timestamps) if timestamps else None,
        },
        "services": dict(services.most_common()),
        "primary_service": services.most_common(1)[0][0] if services else "unknown",
        "revisions": dict(revisions.most_common(20)),
        "commit_shas": dict(commits.most_common(10)),
        "severity_counts": dict(severities),
    }


def extract_http_errors(entries: Sequence[LogEntry], *, max_samples: int = 80) -> Dict[str, Any]:
    by_status: Counter[int] = Counter()
    by_path: Counter[str] = Counter()
    samples: List[Dict[str, Any]] = []
    latencies: Dict[str, List[float]] = defaultdict(list)

    for entry in entries:
        http = entry.http
        if not http:
            continue
        status = int(http.get("status") or 0)
        path = _request_path(http.get("requestUrl", ""))
        method = http.get("requestMethod", "")
        lat = _parse_latency_seconds(http.get("latency", ""))
        if lat is not None:
            latencies[f"{method} {path}"].append(lat)
        if status < 400:
            continue
        by_status[status] += 1
        by_path[f"{method} {path} ({status})"] += 1
        if len(samples) < max_samples:
            samples.append(
                {
                    "timestamp": entry.timestamp,
                    "status": status,
                    "method": method,
                    "path": path,
                    "latency_s": lat,
                    "severity": entry.severity,
                    "revision": (entry.resource.get("labels") or {}).get("revision_name"),
                    "commit_sha": entry.labels.get("commit-sha"),
                }
            )

    slow_paths = {
        key: _stats(vals)
        for key, vals in latencies.items()
        if vals and max(vals) >= 5.0
    }

    return {
        "http_4xx_5xx_total": sum(by_status.values()),
        "by_status": dict(sorted(by_status.items())),
        "by_path": dict(by_path.most_common(30)),
        "slow_endpoints_ge_5s": slow_paths,
        "samples": samples,
    }


def extract_text_errors(entries: Sequence[LogEntry], *, max_samples: int = 80) -> Dict[str, Any]:
    patterns = Counter()
    samples: List[Dict[str, str]] = []

    for entry in entries:
        text = entry.text
        lower = text.lower()
        if not text:
            continue
        is_error = entry.severity in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY") or "[error]" in lower
        if not is_error:
            continue
        if any(noise in lower for noise in ERROR_NOISE):
            continue
        key = text[:120]
        patterns[key] += 1
        if len(samples) < max_samples:
            samples.append(
                {
                    "timestamp": entry.timestamp,
                    "severity": entry.severity,
                    "message": text[:500],
                    "revision": (entry.resource.get("labels") or {}).get("revision_name"),
                }
            )

    return {
        "count": sum(patterns.values()),
        "top_patterns": [{"message": k, "count": v} for k, v in patterns.most_common(25)],
        "samples": samples,
    }


def extract_pipeline_perf(entries: Sequence[LogEntry], *, max_rows: int = 200) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for entry in entries:
        match = PIPELINE_PERF_RE.search(entry.text)
        if not match:
            continue
        parsed = _safe_literal_eval(match.group(1))
        if not parsed:
            continue
        parsed["log_ts"] = entry.timestamp
        rows.append(parsed)

    by_channel: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_channel[str(row.get("channel") or "unknown")].append(row)

    channel_stats: Dict[str, Any] = {}
    for channel, items in by_channel.items():
        totals = [float(i.get("total_ms") or 0) for i in items]
        security_gaps = []
        triage_waits = []
        for item in items:
            breakdown = item.get("breakdown") or {}
            if "before_security" in breakdown and "after_security" in breakdown:
                security_gaps.append(breakdown["after_security"] - breakdown["before_security"])
            if "after_security" in breakdown and "before_triage" in breakdown:
                triage_waits.append(breakdown["before_triage"] - breakdown["after_security"])
        channel_stats[channel] = {
            "count": len(items),
            "total_ms": _stats(totals),
            "security_phase_ms": _stats(security_gaps),
            "triage_wait_after_security_ms": _stats(triage_waits),
            "slowest": sorted(items, key=lambda x: float(x.get("total_ms") or 0), reverse=True)[:10],
        }

    rows_sorted = sorted(rows, key=lambda x: x.get("log_ts", ""))
    if len(rows_sorted) > max_rows:
        rows_sorted = rows_sorted[-max_rows:]

    return {
        "pipeline_perf_count": len(rows),
        "by_channel": channel_stats,
        "recent_rows": rows_sorted,
    }


def extract_llm_cost(entries: Sequence[LogEntry]) -> Dict[str, Any]:
    perf = extract_pipeline_perf(entries, max_rows=10_000)
    calls: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_latency = 0.0
    by_path: Counter[str] = Counter()
    by_model: Counter[str] = Counter()

    for row in perf.get("recent_rows", []):
        llm = row.get("llm") or {}
        for call in llm.get("llm_calls") or []:
            calls.append({**call, "channel": row.get("channel"), "sid": row.get("sid"), "log_ts": row.get("log_ts")})
            total_cost += float(call.get("cost_jpy") or 0)
            total_latency += float(call.get("latency_ms") or 0)
            by_path[str(call.get("path") or "unknown")] += 1
            by_model[str(call.get("model") or "unknown")] += 1

    session_costs: Dict[str, float] = defaultdict(float)
    for row in perf.get("recent_rows", []):
        sid = str(row.get("sid") or "")
        llm = row.get("llm") or {}
        session_costs[sid] += float(llm.get("llm_session_cost_jpy") or 0)

    top_sessions = sorted(session_costs.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "llm_call_count": len(calls),
        "total_cost_jpy": round(total_cost, 4),
        "total_latency_ms": round(total_latency, 2),
        "by_path": dict(by_path.most_common(20)),
        "by_model": dict(by_model.most_common(10)),
        "top_sessions_by_cost": [{"session_id": sid, "cost_jpy": round(cost, 4)} for sid, cost in top_sessions if sid],
        "recent_calls": calls[-80:],
    }


def extract_deploy_revision(entries: Sequence[LogEntry]) -> Dict[str, Any]:
    timeline: List[Dict[str, str]] = []
    seen: set[Tuple[str, str, str]] = set()

    for entry in sorted(entries, key=lambda e: e.timestamp):
        res = entry.resource.get("labels") or {}
        revision = res.get("revision_name")
        commit = entry.labels.get("commit-sha")
        service = res.get("service_name")
        if not revision:
            continue
        key = (service or "", revision, commit or "")
        if key in seen:
            continue
        seen.add(key)
        timeline.append(
            {
                "timestamp": entry.timestamp,
                "service": service,
                "revision": revision,
                "commit_sha": commit,
            }
        )

    return {"revision_timeline": timeline, "revision_count": len(timeline)}


def extract_db_neon(entries: Sequence[LogEntry], *, max_samples: int = 60) -> Dict[str, Any]:
    samples: List[Dict[str, str]] = []
    patterns = Counter()
    for entry in entries:
        text = entry.text
        lower = text.lower()
        if not any(k in lower for k in DB_KEYWORDS):
            continue
        key = text[:100]
        patterns[key] += 1
        if len(samples) < max_samples:
            samples.append({"timestamp": entry.timestamp, "message": text[:400]})
    return {
        "count": sum(patterns.values()),
        "top_patterns": [{"message": k, "count": v} for k, v in patterns.most_common(20)],
        "samples": samples,
    }


def extract_line_webhook(entries: Sequence[LogEntry], *, max_samples: int = 80) -> Dict[str, Any]:
    webhook_latencies: List[float] = []
    lock_events: List[Dict[str, str]] = []
    line_messages: List[Dict[str, str]] = []
    status_counter: Counter[int] = Counter()

    for entry in entries:
        http = entry.http
        if http and "/line/webhook" in (http.get("requestUrl") or ""):
            status = int(http.get("status") or 0)
            status_counter[status] += 1
            lat = _parse_latency_seconds(http.get("latency", ""))
            if lat is not None:
                webhook_latencies.append(lat)
        text = entry.text
        lower = text.lower()
        if any(k in lower for k in LINE_LOCK_KEYWORDS):
            if len(lock_events) < max_samples:
                lock_events.append({"timestamp": entry.timestamp, "message": text[:350]})
        if "LINE text message" in text and len(line_messages) < max_samples:
            line_messages.append({"timestamp": entry.timestamp, "message": text[:250]})

    return {
        "webhook_request_stats": _stats(webhook_latencies),
        "webhook_status_counts": dict(status_counter),
        "job_lock_events": lock_events,
        "line_text_messages": line_messages,
    }


def _trace_id_from_text(text: str) -> Optional[str]:
    match = TRACE_ID_RE.search(text)
    return match.group(1) if match else None


def extract_chat_flow(entries: Sequence[LogEntry], *, max_traces: int = 60) -> Dict[str, Any]:
    traces: Dict[str, Dict[str, Any]] = {}
    current_trace_id: Optional[str] = None

    for entry in entries:
        text = entry.text
        trace_id = _trace_id_from_text(text)
        if not trace_id:
            step_match = AGENT_STEP_RE.search(text)
            if step_match:
                step = _safe_literal_eval(step_match.group(1))
                if step:
                    trace_id = step.get("trace_id")
        if trace_id:
            current_trace_id = str(trace_id)
        elif "POST処理開始" not in text and current_trace_id:
            trace_id = current_trace_id
        if not trace_id:
            continue

        bucket = traces.setdefault(
            trace_id,
            {
                "trace_id": trace_id,
                "events": [],
                "started_at": entry.timestamp,
                "session_id": None,
                "user_message": None,
                "triage": None,
                "concierge_intent": None,
                "pipeline_perf": None,
                "agent_steps": [],
            },
        )

        if "POST処理開始" in text:
            bucket["started_at"] = entry.timestamp
            bucket["events"].append({"ts": entry.timestamp, "type": "post_start"})
        if "User Message:" in text:
            um = USER_MESSAGE_RE.search(text)
            if um:
                bucket["user_message"] = um.group(1).strip()
                bucket["events"].append({"ts": entry.timestamp, "type": "user_message", "text": bucket["user_message"]})
        if "受信メッセージ:" in text:
            rm = RECEIVED_MESSAGE_RE.search(text)
            if rm:
                bucket["user_message"] = bucket["user_message"] or rm.group(1).strip()
                bucket["events"].append({"ts": entry.timestamp, "type": "received_message", "text": rm.group(1).strip()})
        triage = TRIAGE_RESULT_RE.search(text)
        if triage:
            bucket["triage"] = {
                "category": triage.group(1).strip(),
                "subcategory": triage.group(2).strip(),
                "confidence": float(triage.group(3)),
            }
            bucket["events"].append({"ts": entry.timestamp, "type": "triage", **bucket["triage"]})
        for pattern, key in (
            (CONCIERGE_INTENT_RE, "concierge_intent"),
            (STRUCTURAL_INTENT_RE, "structural_intent"),
            (META_INTENT_RE, "meta_intent"),
        ):
            m = pattern.search(text)
            if m:
                bucket[key] = m.group(1)
                bucket["events"].append({"ts": entry.timestamp, "type": key, "value": m.group(1)})
        step_match = AGENT_STEP_RE.search(text)
        if step_match:
            step = _safe_literal_eval(step_match.group(1))
            if step:
                bucket["session_id"] = bucket["session_id"] or step.get("session_id")
                bucket["agent_steps"].append(step)
                bucket["events"].append({"ts": entry.timestamp, "type": "agent_step", "step": step})
        perf_match = PIPELINE_PERF_RE.search(text)
        if perf_match:
            perf = _safe_literal_eval(perf_match.group(1))
            if perf:
                bucket["pipeline_perf"] = perf
                sid = perf.get("sid")
                if sid and not bucket.get("session_id"):
                    bucket["session_id"] = str(sid)
                bucket["events"].append(
                    {
                        "ts": entry.timestamp,
                        "type": "pipeline_perf",
                        "total_ms": perf.get("total_ms"),
                        "channel": perf.get("channel"),
                    }
                )

    trace_list = sorted(traces.values(), key=lambda t: t.get("started_at") or "")
    if len(trace_list) > max_traces:
        trace_list = trace_list[-max_traces:]

    slow_traces = [
        t
        for t in trace_list
        if t.get("pipeline_perf") and float((t["pipeline_perf"] or {}).get("total_ms") or 0) >= 8000
    ]

    return {
        "trace_count": len(traces),
        "exported_traces": trace_list,
        "slow_traces_ge_8s": slow_traces[:30],
    }


def extract_intent_router_logs(entries: Sequence[LogEntry]) -> Dict[str, Any]:
    """dialogue_route_shadow / dialogue_route_dispatch 構造化ログを抽出。"""
    from src.analysis.intent_router_log_analysis import measure_intent_router_logs

    rows = [
        obj
        for obj in _extract_multiline_json_objects(entries)
        if obj.get("log_type") in ("dialogue_route_shadow", "dialogue_route_dispatch")
    ]
    metrics = measure_intent_router_logs(rows)
    return {"rows": rows, **metrics}


def extract_user_sessions(
    entries: Sequence[LogEntry],
    *,
    max_counseling: int = 500,
    max_security_flags: int = 40,
    chat_flow: Optional[Dict[str, Any]] = None,
    max_sessions: int = 50,
) -> Dict[str, Any]:
    counseling_objects = [
        obj
        for obj in _extract_multiline_json_objects(entries)
        if obj.get("log_type") == "counseling_detail"
    ]
    total_counseling = len(counseling_objects)
    counseling_objects, dedup_removed = dedupe_counseling_details(counseling_objects)
    if len(counseling_objects) > max_counseling:
        counseling_objects = counseling_objects[-max_counseling:]

    security_flags: List[Dict[str, Any]] = []
    for entry in entries:
        text = entry.text
        if "security validation" in text.lower() or "run_safety_gate" in text.lower():
            if len(security_flags) < max_security_flags:
                security_flags.append({"timestamp": entry.timestamp, "message": text[:300]})
        if "safe=False" in text or "safe=false" in text.lower():
            if len(security_flags) < max_security_flags:
                security_flags.append({"timestamp": entry.timestamp, "message": text[:300]})

    flow = chat_flow or extract_chat_flow(entries, max_traces=500)
    session_data = build_session_conversations(
        counseling_objects,
        flow,
        max_sessions=max_sessions,
    )
    rec_events = extract_physical_recommendation_events(entries)
    session_data = attach_physical_recommendation_context(session_data, rec_events)
    intent_router = extract_intent_router_logs(entries)

    return {
        "counseling_detail_count": total_counseling,
        "counseling_dedup_removed": dedup_removed,
        "counseling_details_exported": len(counseling_objects),
        "counseling_details": counseling_objects,
        "security_flags": security_flags,
        "session_conversations": session_data,
        "intent_mismatches": session_data.get("intent_mismatches") or [],
        "intent_review_queue": session_data.get("intent_mismatches") or [],
        "sessions_by_grade": session_data.get("sessions_by_grade") or {},
        "intent_router": intent_router,
    }


def extract_misc_signals(entries: Sequence[LogEntry], *, max_samples: int = 50) -> Dict[str, Any]:
    """その他の追跡可能シグナル（予算、緊急検出、重複トリアージ等）。"""
    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    keywords = {
        "budget": ("budget",),
        "emergency": ("緊急事案検出", "emergency"),
        "moderation": ("moderationagent", "run_safety_gate"),
        "duplicate_triage": ("triage", "duplicate", "skipping"),
        "gunicorn": ("gunicorn", "worker", "booting"),
        "openai_errors": ("openai", "rate limit", "timeout", "api error"),
    }

    for entry in entries:
        lower = entry.text.lower()
        for name, terms in keywords.items():
            if any(t in lower for t in terms):
                if len(buckets[name]) < max_samples:
                    buckets[name].append({"timestamp": entry.timestamp, "message": entry.text[:350]})

    return {name: items for name, items in buckets.items() if items}


SECTION_BUILDERS: Dict[str, Any] = {
    "errors_http": lambda e, **kw: {
        "http": extract_http_errors(e, max_samples=kw.get("max_samples", 80)),
        "text_errors": extract_text_errors(e, max_samples=kw.get("max_samples", 80)),
    },
    "pipeline_perf": extract_pipeline_perf,
    "llm_cost": extract_llm_cost,
    "deploy_revision": extract_deploy_revision,
    "db_neon": extract_db_neon,
    "line_webhook": extract_line_webhook,
    "chat_flow": extract_chat_flow,
    "user_sessions": extract_user_sessions,
    "misc_signals": extract_misc_signals,
}


def build_analysis_bundle_from_entries(
    entries: Sequence[LogEntry],
    source_path: Path,
    *,
    max_samples: int = 80,
    max_traces: int = 200,
    max_counseling: int = 500,
    max_sessions: int = 50,
    environment: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = extract_metadata(entries, source_path)
    if environment:
        metadata["environment"] = environment
        metadata["primary_service"] = environment
    chat_flow = extract_chat_flow(entries, max_traces=max_traces)
    sections: Dict[str, Any] = {}

    for name, builder in SECTION_BUILDERS.items():
        if name == "pipeline_perf":
            sections[name] = builder(entries, max_rows=200)
        elif name == "chat_flow":
            sections[name] = chat_flow
        elif name == "user_sessions":
            sections[name] = extract_user_sessions(
                entries,
                max_counseling=max_counseling,
                chat_flow=chat_flow,
                max_sessions=max_sessions,
            )
        elif name == "errors_http":
            sections[name] = builder(entries, max_samples=max_samples)
        elif name in ("db_neon", "line_webhook", "misc_signals"):
            sections[name] = builder(entries, max_samples=max_samples)
        else:
            sections[name] = builder(entries)

    return {"metadata": metadata, "sections": sections}


def build_analysis_bundle(
    source_path: Path,
    *,
    max_samples: int = 80,
    max_traces: int = 200,
    max_counseling: int = 500,
    max_sessions: int = 50,
) -> Dict[str, Any]:
    entries = load_gcp_log_entries(source_path)
    return build_analysis_bundle_from_entries(
        entries,
        source_path,
        max_samples=max_samples,
        max_traces=max_traces,
        max_counseling=max_counseling,
        max_sessions=max_sessions,
    )


def build_analysis_bundle_from_dev_logs(
    paths: Sequence[Path],
    *,
    output_label: Optional[str] = None,
    max_samples: int = 80,
    max_traces: int = 200,
    max_counseling: int = 500,
    max_sessions: int = 50,
) -> Dict[str, Any]:
    """複数の開発 Markdown ログを時系列マージして解析バンドルを構築する。"""
    entries: List[LogEntry] = []
    for path in paths:
        entries.extend(load_dev_markdown_log_entries(path))
    entries.sort(key=lambda e: e.timestamp or "")
    label = output_label or "+".join(p.stem for p in paths)
    virtual_source = paths[0].parent / f"{label}.md"
    return build_analysis_bundle_from_entries(
        entries,
        virtual_source,
        max_samples=max_samples,
        max_traces=max_traces,
        max_counseling=max_counseling,
        max_sessions=max_sessions,
        environment="local-dev",
    )


def write_analysis_bundle(
    bundle: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    paths: Dict[str, str] = {}
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(bundle["metadata"], ensure_ascii=False, indent=2), encoding="utf-8")
    paths["metadata"] = str(meta_path)

    for name, payload in bundle["sections"].items():
        path = sections_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[name] = str(path)

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metadata_path": paths["metadata"],
        "sections": paths,
        "analysis_groups": {
            "infra_errors": ["errors_http", "deploy_revision"],
            "performance_cost": ["pipeline_perf", "llm_cost"],
            "conversation_quality": ["chat_flow", "user_sessions"],
            "integrations": ["line_webhook", "db_neon", "misc_signals"],
        },
        "conversation_quality_focus": {
            "session_timelines": "user_sessions.session_conversations.sessions",
            "conversation_history": "sessions[].conversation_history / turns[].conversation_history",
            "heuristic_hints": "user_sessions.intent_mismatches (LLM must re-judge)",
            "physical_advisor": "sessions[].physical_recommendation_summary",
            "quality_summary": "quality_metrics.json",
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["manifest"] = str(manifest_path)

    sc = bundle.get("sections", {}).get("user_sessions", {}).get("session_conversations")
    if sc:
        session_md_paths = write_session_transcripts(sc, output_dir)
        manifest["session_transcripts"] = session_md_paths
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["session_transcripts_dir"] = str(output_dir / "sessions")

    quality = build_quality_metrics(bundle)
    quality_path = output_dir / "quality_metrics.json"
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["quality_metrics"] = str(quality_path)

    return paths
