"""
ローカルに保存済みの GCP ログエクスポート／解析結果からカバレッジを推定する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.analysis.gcp_log_export import format_timestamp, parse_timestamp

EXPORT_STATE_REL = Path("log/raw/export_state.json")
ANALYSIS_METADATA_GLOB = "log/analysis/*/metadata.json"


@dataclass(frozen=True)
class CoverageRecord:
    service: str
    start: datetime
    end: datetime
    source_path: str
    source_kind: str
    entry_count: Optional[int] = None


def _parse_meta_time_range(payload: Dict[str, Any]) -> Optional[tuple[datetime, datetime]]:
    time_range = payload.get("time_range") or {}
    start_raw = time_range.get("start")
    end_raw = time_range.get("end")
    if not start_raw or not end_raw:
        return None
    return parse_timestamp(str(start_raw)), parse_timestamp(str(end_raw))


def load_export_state(project_root: Path) -> Dict[str, Any]:
    path = project_root / EXPORT_STATE_REL
    if not path.is_file():
        return {"by_service": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"by_service": {}}
    if not isinstance(data, dict):
        return {"by_service": {}}
    by_service = data.get("by_service")
    if not isinstance(by_service, dict):
        return {"by_service": {}}
    return data


def save_export_state(project_root: Path, record: CoverageRecord, *, exported_at: Optional[datetime] = None) -> Path:
    path = project_root / EXPORT_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    state = load_export_state(project_root)
    by_service = state.setdefault("by_service", {})
    by_service[record.service] = {
        "last_start": format_timestamp(record.start),
        "last_end": format_timestamp(record.end),
        "source_path": record.source_path,
        "source_kind": record.source_kind,
        "entry_count": record.entry_count,
        "exported_at": format_timestamp(exported_at or datetime.now(timezone.utc)),
    }
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _records_from_export_state(project_root: Path) -> List[CoverageRecord]:
    records: List[CoverageRecord] = []
    for service, payload in (load_export_state(project_root).get("by_service") or {}).items():
        if not isinstance(payload, dict):
            continue
        try:
            start = parse_timestamp(str(payload["last_start"]))
            end = parse_timestamp(str(payload["last_end"]))
        except (KeyError, ValueError):
            continue
        records.append(
            CoverageRecord(
                service=str(service),
                start=start,
                end=end,
                source_path=str(payload.get("source_path") or ""),
                source_kind=str(payload.get("source_kind") or "export_state"),
                entry_count=payload.get("entry_count"),
            )
        )
    return records


def _records_from_analysis_metadata(project_root: Path) -> List[CoverageRecord]:
    records: List[CoverageRecord] = []
    for meta_path in sorted((project_root / "log/analysis").glob("*/metadata.json")):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        parsed = _parse_meta_time_range(payload)
        if not parsed:
            continue
        start, end = parsed
        records.append(
            CoverageRecord(
                service=str(payload.get("primary_service") or "unknown"),
                start=start,
                end=end,
                source_path=str(payload.get("source_path") or meta_path.as_posix()),
                source_kind="analysis_metadata",
                entry_count=payload.get("entry_count"),
            )
        )
    return records


def collect_coverage_records(project_root: Path) -> List[CoverageRecord]:
    merged: Dict[tuple[str, str], CoverageRecord] = {}
    for record in [* _records_from_analysis_metadata(project_root), *_records_from_export_state(project_root)]:
        key = (record.service, record.source_path or record.source_kind)
        existing = merged.get(key)
        if existing is None or record.end > existing.end:
            merged[key] = record
    return list(merged.values())


def find_latest_coverage(project_root: Path, service: Optional[str] = None) -> Optional[CoverageRecord]:
    candidates = collect_coverage_records(project_root)
    if service:
        candidates = [item for item in candidates if item.service == service]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.end)


def resolve_incremental_range(
    project_root: Path,
    *,
    service: str,
    end: Optional[datetime] = None,
    min_gap_seconds: int = 60,
    overlap_seconds: int = 30,
) -> Optional[tuple[datetime, datetime, CoverageRecord]]:
    latest = find_latest_coverage(project_root, service=service)
    if latest is None:
        return None

    end_dt = end or datetime.now(timezone.utc)
    start_dt = latest.end - timedelta(seconds=max(0, overlap_seconds))
    if start_dt >= end_dt:
        return None
    if (end_dt - start_dt).total_seconds() < min_gap_seconds:
        return None
    return start_dt, end_dt, latest
