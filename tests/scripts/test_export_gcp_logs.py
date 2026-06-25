"""export_gcp_logs.py のユニットテスト。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.analysis.gcp_log_export import (
    build_log_filter,
    export_logs,
    iter_time_windows,
    merge_log_entries,
    parse_freshness,
    parse_timestamp,
    resolve_time_range,
)


def test_parse_timestamp_z_suffix():
    dt = parse_timestamp("2026-06-24T18:08:04Z")
    assert dt == datetime(2026, 6, 24, 18, 8, 4, tzinfo=timezone.utc)


def test_parse_freshness_hours():
    assert parse_freshness("10h").total_seconds() == 10 * 3600


def test_resolve_time_range_with_freshness():
    start, end = resolve_time_range(None, None, "1h")
    assert start < end
    assert (end - start).total_seconds() == pytest.approx(3600, rel=0.01)


def test_iter_time_windows_splits_range():
    start = datetime(2026, 6, 24, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 24, 10, 0, tzinfo=timezone.utc)
    windows = list(iter_time_windows(start, end, chunk_hours=4))
    assert windows == [
        (start, datetime(2026, 6, 24, 4, 0, tzinfo=timezone.utc)),
        (datetime(2026, 6, 24, 4, 0, tzinfo=timezone.utc), datetime(2026, 6, 24, 8, 0, tzinfo=timezone.utc)),
        (datetime(2026, 6, 24, 8, 0, tzinfo=timezone.utc), end),
    ]


def test_build_log_filter_includes_service_and_window():
    start = datetime(2026, 6, 24, 18, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 24, 22, 0, tzinfo=timezone.utc)
    filt = build_log_filter(
        window_start=start,
        window_end=end,
        service="medicine-recommend-dev",
        extra_filter='textPayload:"PIPELINE_PERF"',
    )
    assert 'resource.labels.service_name="medicine-recommend-dev"' in filt
    assert 'timestamp>="2026-06-24T18:00:00Z"' in filt
    assert 'timestamp<="2026-06-24T22:00:00Z"' in filt
    assert 'textPayload:"PIPELINE_PERF"' in filt


def test_merge_log_entries_dedupes_insert_id_and_sorts():
    merged = merge_log_entries(
        [
            [
                {"insertId": "b", "timestamp": "2026-06-24T02:00:00Z"},
                {"insertId": "a", "timestamp": "2026-06-24T01:00:00Z"},
            ],
            [
                {"insertId": "a", "timestamp": "2026-06-24T01:00:00Z"},
                {"insertId": "c", "timestamp": "2026-06-24T03:00:00Z"},
            ],
        ]
    )
    assert [item["insertId"] for item in merged] == ["a", "b", "c"]


def test_export_logs_uses_injected_fetcher():
    start = datetime(2026, 6, 24, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 24, 4, 0, tzinfo=timezone.utc)

    def fake_fetcher(**kwargs):
        return [{"insertId": "x", "timestamp": "2026-06-24T01:00:00Z"}]

    entries, reports = export_logs(
        project_id="test-project",
        start=start,
        end=end,
        service="medicine-recommend-dev",
        extra_filter=None,
        chunk_hours=4,
        limit_per_chunk=100,
        fetcher=fake_fetcher,
    )
    assert len(entries) == 1
    assert len(reports) == 1
    assert reports[0]["entry_count"] == 1
