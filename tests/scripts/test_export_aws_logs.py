"""export_aws_logs.py のユニットテスト。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.analysis.aws_log_export import (
    export_logs,
    merge_log_events,
    resolve_log_group,
    resolve_region,
)
from src.analysis.gcp_log_export import iter_time_windows


def test_resolve_log_group_from_service():
    assert resolve_log_group("medicine-recommend", None) == "/ecs/medicine-recommend"


def test_resolve_log_group_explicit():
    assert resolve_log_group(None, "/custom/group") == "/custom/group"


def test_iter_time_windows_splits_range():
    start = datetime(2026, 6, 24, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 24, 10, 0, tzinfo=timezone.utc)
    windows = list(iter_time_windows(start, end, chunk_hours=4))
    assert len(windows) == 3


def test_merge_log_events_dedupes_event_id_and_sorts():
    merged = merge_log_events(
        [
            [
                {"eventId": "b", "timestamp": 2000},
                {"eventId": "a", "timestamp": 1000},
            ],
            [
                {"eventId": "a", "timestamp": 1000},
                {"eventId": "c", "timestamp": 3000},
            ],
        ]
    )
    assert [item["eventId"] for item in merged] == ["a", "b", "c"]


def test_export_logs_uses_injected_fetcher():
    start = datetime(2026, 6, 24, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 24, 4, 0, tzinfo=timezone.utc)

    def fake_fetcher(**kwargs):
        return [{"eventId": "x", "timestamp": 1719187200100, "message": "hello"}]

    entries, reports = export_logs(
        log_group="/ecs/medicine-recommend",
        region="ap-northeast-1",
        start=start,
        end=end,
        filter_pattern=None,
        chunk_hours=4,
        limit_per_chunk=100,
        fetcher=fake_fetcher,
    )
    assert len(entries) == 1
    assert len(reports) == 1
    assert reports[0]["entry_count"] == 1


def test_resolve_region_default():
    assert resolve_region(None) == "ap-northeast-1"
