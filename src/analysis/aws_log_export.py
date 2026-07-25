"""
AWS CloudWatch Logs の時間分割エクスポート（aws logs filter-log-events ラッパー）。

Console / Logs Insights の 1 万件制限を超える取得を、JSON 配列形式で行う。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from typing import Callable, Iterable, List, Optional, Sequence

from src.analysis.gcp_log_export import format_timestamp, iter_time_windows
from src.analysis.log_secret_redaction import redact_object

DEFAULT_LOG_GROUP = "/ecs/medicine-recommend"
DEFAULT_REGION = "ap-northeast-1"
DEFAULT_ECS_SERVICE = "medicine-recommend"


def datetime_to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def build_log_filter_pattern(extra_filter: Optional[str]) -> Optional[str]:
    if not extra_filter or not extra_filter.strip():
        return None
    return extra_filter.strip()


def merge_log_events(chunks: Iterable[Sequence[dict]]) -> List[dict]:
    merged: List[dict] = []
    seen: set[str] = set()
    for events in chunks:
        for event in events:
            event_id = str(event.get("eventId") or "")
            if event_id:
                if event_id in seen:
                    continue
                seen.add(event_id)
            merged.append(event)
    merged.sort(key=lambda item: item.get("timestamp") or 0)
    return merged


def _aws_executable() -> str:
    path = shutil.which("aws")
    if not path:
        raise RuntimeError("aws CLI not found")
    return path


def resolve_region(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    import os

    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION


def resolve_log_group(service: Optional[str], explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    if service:
        return f"/ecs/{service}"
    return DEFAULT_LOG_GROUP


def fetch_log_events(
    *,
    log_group: str,
    region: str,
    start_ms: int,
    end_ms: int,
    filter_pattern: Optional[str],
    limit: int,
    profile: Optional[str] = None,
) -> List[dict]:
    try:
        aws = _aws_executable()
    except RuntimeError as exc:
        raise RuntimeError("aws CLI not found") from exc

    events: List[dict] = []
    next_token: Optional[str] = None

    while len(events) < limit:
        page_limit = min(10_000, limit - len(events))
        cmd = [
            aws,
            "logs",
            "filter-log-events",
            "--log-group-name",
            log_group,
            "--start-time",
            str(start_ms),
            "--end-time",
            str(end_ms),
            "--limit",
            str(page_limit),
            "--region",
            region,
            "--output",
            "json",
        ]
        if filter_pattern:
            cmd.extend(["--filter-pattern", filter_pattern])
        if profile:
            cmd.extend(["--profile", profile])
        if next_token:
            cmd.extend(["--next-token", next_token])

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "aws logs filter-log-events failed").strip()
            raise RuntimeError(message)

        payload = json.loads(result.stdout or "{}")
        page_events = payload.get("events") or []
        if not isinstance(page_events, list):
            raise ValueError("Expected events array from aws logs filter-log-events")
        events.extend(page_events)
        next_token = payload.get("nextToken")
        if not next_token or not page_events:
            break

    return events[:limit]


Fetcher = Callable[..., List[dict]]


def export_logs(
    *,
    log_group: str,
    region: str,
    start: datetime,
    end: datetime,
    filter_pattern: Optional[str],
    chunk_hours: float,
    limit_per_chunk: int,
    profile: Optional[str] = None,
    dry_run: bool = False,
    fetcher: Fetcher = fetch_log_events,
    on_chunk=None,
) -> tuple[List[dict], list[dict]]:
    chunk_reports: list[dict] = []
    chunk_events: list[List[dict]] = []

    for index, (window_start, window_end) in enumerate(
        iter_time_windows(start, end, chunk_hours),
        start=1,
    ):
        start_ms = datetime_to_epoch_ms(window_start)
        end_ms = datetime_to_epoch_ms(window_end)
        report = {
            "chunk": index,
            "start": format_timestamp(window_start),
            "end": format_timestamp(window_end),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "log_group": log_group,
            "filter_pattern": filter_pattern,
            "entry_count": 0,
            "truncated": False,
        }
        if dry_run:
            chunk_reports.append(report)
            continue

        events = fetcher(
            log_group=log_group,
            region=region,
            start_ms=start_ms,
            end_ms=end_ms,
            filter_pattern=filter_pattern,
            limit=limit_per_chunk,
            profile=profile,
        )
        report["entry_count"] = len(events)
        report["truncated"] = len(events) >= limit_per_chunk
        chunk_reports.append(report)
        chunk_events.append(events)
        if on_chunk is not None:
            on_chunk(report)

    if dry_run:
        return [], chunk_reports

    merged = merge_log_events(chunk_events)
    redacted = [redact_object(event) for event in merged]
    return redacted, chunk_reports
