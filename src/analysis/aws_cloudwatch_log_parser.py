"""
AWS CloudWatch Logs エクスポート JSON（downloaded-aws-logs-*.json）の解析。

CloudWatch イベントを GCP 互換 LogEntry に正規化し、既存のセクション抽出ロジックを再利用する。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.analysis.gcp_cloud_run_log_parser import (
    LogEntry,
    build_analysis_bundle_from_entries,
    write_analysis_bundle,
)
from src.analysis.log_secret_redaction import redact_object

PYTHON_LOG_SEVERITY_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (\w+) - ",
)
HTTP_STATUS_IN_TEXT_RE = re.compile(
    r'"(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^\s"]+)\s+HTTP/[\d.]+"\s+(\d{3})',
)
ECS_TASK_DEF_RE = re.compile(r"task-definition/([^:/\s]+):(\d+)")
DEPLOY_NOISE = (
    "was sent sigterm",
    "worker (pid:",
    "gunicorn",
)


def _epoch_ms_to_iso(ms: int) -> str:
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _severity_from_message(message: str) -> str:
    match = PYTHON_LOG_SEVERITY_RE.match(message.strip())
    if match:
        return match.group(1).upper()
    lower = message.lower()
    if " - error - " in lower or "[error]" in lower:
        return "ERROR"
    if " - warning - " in lower or "[warning]" in lower:
        return "WARNING"
    return "INFO"


def _task_revision_from_stream(log_stream: str) -> Optional[str]:
    if not log_stream:
        return None
    parts = log_stream.split("/")
    if len(parts) >= 2:
        return parts[-1][:12]
    return None


def LogEntry_from_cloudwatch(raw: Dict[str, Any], *, log_group: str = "") -> LogEntry:
    message = str(raw.get("message") or "")
    timestamp_ms = int(raw.get("timestamp") or 0)
    log_stream = str(raw.get("logStreamName") or "")
    ingestion_ms = raw.get("ingestionTime")
    labels: Dict[str, str] = {
        "log_stream": log_stream,
        "event_id": str(raw.get("eventId") or ""),
    }
    if ingestion_ms:
        labels["ingestion_time_ms"] = str(ingestion_ms)

    http = None
    http_match = HTTP_STATUS_IN_TEXT_RE.search(message)
    if http_match:
        path = http_match.group(1)
        status = int(http_match.group(2))
        http = {
            "requestMethod": "UNKNOWN",
            "requestUrl": path if path.startswith("/") else f"/{path}",
            "status": status,
            "latency": "",
        }

    resource = {
        "type": "aws_ecs_container",
        "labels": {
            "log_group": log_group,
            "log_stream": log_stream,
            "task_revision_hint": _task_revision_from_stream(log_stream) or "",
        },
    }

    return LogEntry(
        timestamp=_epoch_ms_to_iso(timestamp_ms) if timestamp_ms else "",
        severity=_severity_from_message(message),
        text=message,
        http=http,
        labels=labels,
        resource=resource,
        log_name=log_group,
        trace="",
        insert_id=str(raw.get("eventId") or ""),
    )


def load_aws_log_entries(path: Path, *, log_group: str = "") -> List[LogEntry]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    redacted = [redact_object(item) for item in data]
    group = log_group
    if not group and redacted:
        first = redacted[0]
        if isinstance(first, dict):
            group = str(first.get("logGroupName") or "")
    return [LogEntry_from_cloudwatch(item, log_group=group) for item in redacted if isinstance(item, dict)]


def extract_aws_metadata(
    entries: Sequence[LogEntry],
    source_path: Path,
    *,
    log_group: str,
    region: str,
    ecs_service: str,
) -> Dict[str, Any]:
    timestamps = [e.timestamp for e in entries if e.timestamp]
    severities = Counter(e.severity for e in entries if e.severity)
    log_streams = Counter(e.labels.get("log_stream", "") for e in entries if e.labels.get("log_stream"))
    task_defs: Counter[str] = Counter()
    commits: Counter[str] = Counter()

    for entry in entries:
        text = entry.text
        for match in ECS_TASK_DEF_RE.finditer(text):
            task_defs[f"{match.group(1)}:{match.group(2)}"] += 1
        commit_match = re.search(r"commit[-_ ]?sha[=:\s]+([0-9a-f]{7,40})", text, re.I)
        if commit_match:
            commits[commit_match.group(1)[:12]] += 1

    return {
        "platform": "aws",
        "source_path": str(source_path),
        "source_name": source_path.name,
        "entry_count": len(entries),
        "time_range": {
            "start": min(timestamps) if timestamps else None,
            "end": max(timestamps) if timestamps else None,
        },
        "log_group": log_group,
        "region": region,
        "ecs_service": ecs_service,
        "primary_service": log_group,
        "services": {log_group: len(entries)},
        "log_streams": dict(log_streams.most_common(20)),
        "task_definitions": dict(task_defs.most_common(20)),
        "commit_shas": dict(commits.most_common(10)),
        "severity_counts": dict(severities),
        "revisions": dict(task_defs.most_common(20)),
    }


def build_aws_analysis_bundle(
    source_path: Path,
    *,
    log_group: str = "",
    region: str = "ap-northeast-1",
    ecs_service: str = "medicine-recommend",
    max_samples: int = 80,
    max_traces: int = 200,
    max_counseling: int = 500,
    max_sessions: int = 50,
) -> Dict[str, Any]:
    entries = load_aws_log_entries(source_path, log_group=log_group)
    inferred_group = log_group or (entries[0].log_name if entries else "/ecs/medicine-recommend")
    bundle = build_analysis_bundle_from_entries(
        entries,
        source_path,
        max_samples=max_samples,
        max_traces=max_traces,
        max_counseling=max_counseling,
        max_sessions=max_sessions,
    )
    aws_meta = extract_aws_metadata(
        entries,
        source_path,
        log_group=inferred_group,
        region=region,
        ecs_service=ecs_service,
    )
    bundle["metadata"] = {**bundle["metadata"], **aws_meta}
    return bundle


def write_aws_analysis_bundle(bundle: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    manifest = write_analysis_bundle(bundle, output_dir)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["platform"] = "aws"
        payload["analysis_groups"] = payload.get("analysis_groups") or {
            "infra_errors": ["errors_http", "deploy_revision"],
            "performance_cost": ["pipeline_perf", "llm_cost"],
            "conversation_quality": ["chat_flow", "user_sessions"],
            "integrations": ["line_webhook", "db_neon", "misc_signals"],
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
