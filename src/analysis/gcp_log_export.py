"""
GCP Cloud Logging の時間分割エクスポート（gcloud logging read ラッパー）。

Console ダウンロード（最大 1 万件）を超える取得を、JSON 配列形式で行う。
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator, List, Optional, Sequence

DEFAULT_PROJECT_ID = "340042923793"
FRESHNESS_RE = re.compile(r"^(\d+)([dhms])$", re.I)


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_freshness(value: str) -> timedelta:
    match = FRESHNESS_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid freshness: {value!r} (expected e.g. 10h, 1d, 30m)")
    amount = int(match.group(1))
    unit = match.group(2).lower()
    if unit == "d":
        return timedelta(days=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    return timedelta(seconds=amount)


def resolve_time_range(
    start: Optional[str],
    end: Optional[str],
    freshness: Optional[str],
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if start and end:
        start_dt = parse_timestamp(start)
        end_dt = parse_timestamp(end)
    elif freshness:
        start_dt = now - parse_freshness(freshness)
        end_dt = now
    else:
        raise ValueError("Specify --start and --end, or --freshness")

    if start_dt >= end_dt:
        raise ValueError(f"Invalid range: start {format_timestamp(start_dt)} >= end {format_timestamp(end_dt)}")
    return start_dt, end_dt


def iter_time_windows(start: datetime, end: datetime, chunk_hours: float) -> Iterator[tuple[datetime, datetime]]:
    if chunk_hours <= 0:
        raise ValueError("chunk_hours must be positive")
    delta = timedelta(hours=chunk_hours)
    cursor = start
    while cursor < end:
        window_end = min(cursor + delta, end)
        yield cursor, window_end
        cursor = window_end


def build_log_filter(
    *,
    window_start: datetime,
    window_end: datetime,
    service: Optional[str],
    extra_filter: Optional[str],
) -> str:
    parts: List[str] = []
    if service:
        parts.append('resource.type="cloud_run_revision"')
        parts.append(f'resource.labels.service_name="{service}"')
    parts.append(f'timestamp>="{format_timestamp(window_start)}"')
    parts.append(f'timestamp<="{format_timestamp(window_end)}"')
    if extra_filter:
        parts.append(f"({extra_filter.strip()})")
    return "\n".join(parts)


def merge_log_entries(chunks: Iterable[Sequence[dict]]) -> List[dict]:
    merged: List[dict] = []
    seen: set[str] = set()
    for entries in chunks:
        for entry in entries:
            insert_id = str(entry.get("insertId") or "")
            if insert_id:
                if insert_id in seen:
                    continue
                seen.add(insert_id)
            merged.append(entry)
    merged.sort(key=lambda item: item.get("timestamp") or "")
    return merged


def resolve_project_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    cmd = ["gcloud", "config", "get-value", "project"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return DEFAULT_PROJECT_ID
    project = (result.stdout or "").strip()
    if result.returncode == 0 and project and project != "(unset)":
        return project
    return DEFAULT_PROJECT_ID


def fetch_log_entries(
    *,
    project_id: str,
    log_filter: str,
    limit: int,
    order: str = "asc",
) -> List[dict]:
    cmd = [
        "gcloud",
        "logging",
        "read",
        log_filter,
        f"--project={project_id}",
        "--format=json",
        f"--order={order}",
        f"--limit={limit}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("gcloud CLI not found") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "gcloud logging read failed").strip()
        raise RuntimeError(message)

    text = (result.stdout or "").strip()
    if not text:
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array from gcloud logging read")
    return data


def export_logs(
    *,
    project_id: str,
    start: datetime,
    end: datetime,
    service: Optional[str],
    extra_filter: Optional[str],
    chunk_hours: float,
    limit_per_chunk: int,
    dry_run: bool = False,
    fetcher=fetch_log_entries,
    on_chunk=None,
) -> tuple[List[dict], list[dict]]:
    chunk_reports: list[dict] = []
    chunk_entries: list[List[dict]] = []

    for index, (window_start, window_end) in enumerate(
        iter_time_windows(start, end, chunk_hours),
        start=1,
    ):
        log_filter = build_log_filter(
            window_start=window_start,
            window_end=window_end,
            service=service,
            extra_filter=extra_filter,
        )
        report = {
            "chunk": index,
            "start": format_timestamp(window_start),
            "end": format_timestamp(window_end),
            "filter": log_filter,
            "entry_count": 0,
            "truncated": False,
        }
        if dry_run:
            chunk_reports.append(report)
            continue

        entries = fetcher(
            project_id=project_id,
            log_filter=log_filter,
            limit=limit_per_chunk,
        )
        report["entry_count"] = len(entries)
        report["truncated"] = len(entries) >= limit_per_chunk
        chunk_reports.append(report)
        chunk_entries.append(entries)
        if on_chunk is not None:
            on_chunk(report)

    if dry_run:
        return [], chunk_reports

    return merge_log_entries(chunk_entries), chunk_reports
