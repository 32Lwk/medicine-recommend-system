"""pipeline_perf の sid キー計測（ワーカースレッド境界）"""
from __future__ import annotations

import threading
from unittest.mock import patch

from src.services.llm_metrics import get_llm_summary, record_llm_call, reset_llm_metrics
from src.services.pipeline_perf import (
    activate_pipeline_perf,
    bind_pipeline_perf,
    log_pipeline_perf,
    mark_pipeline_step,
)


def test_worker_thread_marks_visible_in_main_thread_log():
    sid = "line-test-sid"
    bind_pipeline_perf(sid=sid, channel="line")
    mark_pipeline_step("line_loading_start")

    def worker():
        activate_pipeline_perf(sid)
        reset_llm_metrics()
        mark_pipeline_step("post_start")
        record_llm_call(model="gpt-test", path="triage.stage1", latency_ms=123.4)

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    mark_pipeline_step("line_reply_done")

    with patch("src.services.pipeline_perf.logger") as mock_logger:
        log_pipeline_perf(sid=sid)
        payload = mock_logger.info.call_args[0][1]

    assert payload["sid"] == sid
    assert "line_loading_start" in payload["breakdown"]
    assert "post_start" in payload["breakdown"]
    assert "line_reply_done" in payload["breakdown"]
    assert payload["llm"]["llm_call_count"] == 1
    assert payload["llm"]["llm_total_latency_ms"] == 123.4


def test_bind_does_not_reset_existing_bucket():
    sid = "line-no-reset"
    bind_pipeline_perf(sid=sid, channel="line")
    mark_pipeline_step("first")

    bind_pipeline_perf(sid=sid, channel="line")
    mark_pipeline_step("second")

    summary = get_llm_summary()
    assert summary["llm_call_count"] == 0

    with patch("src.services.pipeline_perf.logger") as mock_logger:
        log_pipeline_perf(sid=sid)
        payload = mock_logger.info.call_args[0][1]

    assert "first" in payload["breakdown"]
    assert "second" in payload["breakdown"]
