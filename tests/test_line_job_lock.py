"""LINE ジョブロックのテスト。"""
from __future__ import annotations

from src.handlers.line.line_job_lock import LineJobLock


def test_line_job_lock_serializes_same_sid():
    lock_a = LineJobLock()
    lock_b = LineJobLock()
    sid = "line:test-lock"
    assert lock_a.acquire(sid) is True
    assert lock_b.acquire(sid) is False
    lock_a.release(sid)
    assert lock_b.acquire(sid) is True
    lock_b.release(sid)
