"""gcp_log_local_state / prepare_gcp_log_analysis のテスト。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.analysis.gcp_log_local_state import (
    find_latest_coverage,
    resolve_incremental_range,
    save_export_state,
    CoverageRecord,
)


def _write_analysis_meta(root: Path, stem: str, *, service: str, start: str, end: str) -> None:
    meta_dir = root / "log/analysis" / stem
    meta_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_path": f"/tmp/{stem}.json",
        "entry_count": 100,
        "time_range": {"start": start, "end": end},
        "primary_service": service,
    }
    (meta_dir / "metadata.json").write_text(json.dumps(payload), encoding="utf-8")


def test_find_latest_coverage_from_analysis_metadata(tmp_path: Path):
    _write_analysis_meta(
        tmp_path,
        "older",
        service="medicine-recommend-dev",
        start="2026-06-24T00:00:00Z",
        end="2026-06-24T10:00:00Z",
    )
    _write_analysis_meta(
        tmp_path,
        "newer",
        service="medicine-recommend-dev",
        start="2026-06-24T10:00:00Z",
        end="2026-06-25T04:13:20Z",
    )

    latest = find_latest_coverage(tmp_path, service="medicine-recommend-dev")
    assert latest is not None
    assert latest.end == datetime(2026, 6, 25, 4, 13, 20, tzinfo=timezone.utc)
    assert latest.source_kind == "analysis_metadata"


def test_resolve_incremental_range_returns_gap(tmp_path: Path, monkeypatch):
    _write_analysis_meta(
        tmp_path,
        "baseline",
        service="medicine-recommend-dev",
        start="2026-06-24T00:00:00Z",
        end="2026-06-25T04:13:20Z",
    )
    fixed_now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    result = resolve_incremental_range(
        tmp_path,
        service="medicine-recommend-dev",
        end=fixed_now,
        min_gap_seconds=60,
        overlap_seconds=30,
    )
    assert result is not None
    start, end, latest = result
    assert latest.end == datetime(2026, 6, 25, 4, 13, 20, tzinfo=timezone.utc)
    assert start < end
    assert end == fixed_now


def test_resolve_incremental_range_no_gap(tmp_path: Path):
    _write_analysis_meta(
        tmp_path,
        "baseline",
        service="medicine-recommend-dev",
        start="2026-06-24T00:00:00Z",
        end="2026-06-25T04:13:20Z",
    )
    result = resolve_incremental_range(
        tmp_path,
        service="medicine-recommend-dev",
        end=datetime(2026, 6, 25, 4, 13, 40, tzinfo=timezone.utc),
        min_gap_seconds=60,
    )
    assert result is None


def test_save_export_state_roundtrip(tmp_path: Path):
    record = CoverageRecord(
        service="medicine-recommend-dev",
        start=datetime(2026, 6, 24, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 6, 25, 4, 13, 20, tzinfo=timezone.utc),
        source_path=str(tmp_path / "log/raw/sample.json"),
        source_kind="export",
        entry_count=42,
    )
    save_export_state(tmp_path, record)
    latest = find_latest_coverage(tmp_path, service="medicine-recommend-dev")
    assert latest is not None
    assert latest.entry_count == 42
    assert latest.source_kind == "export"
