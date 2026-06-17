"""feedback_trace 非同期保存"""
from unittest.mock import patch

from src.services.feedback_trace import build_feedback_trace, submit_feedback_async


def test_build_feedback_trace():
    trace = build_feedback_trace(
        source="line",
        event="feedback_postback",
        session_id="line:U1",
        report_type="positive_feedback",
    )
    assert trace["source"] == "line"
    assert trace["event"] == "feedback_postback"
    assert trace["session_id"] == "line:U1"
    assert "recorded_at" in trace


@patch("src.services.feedback_submit.submit_feedback_record", return_value={"status": "success", "feedback_id": 3})
def test_submit_feedback_async_runs_in_background(mock_submit):
    submit_feedback_async(
        report_type="slow_request",
        session_id="sid-1",
        username="user",
        user_message="頭痛",
        ai_response="処理中",
        metadata={"source": "web", "event": "slow_request_notify"},
        dedupe=False,
    )
    import time

    time.sleep(0.2)
    mock_submit.assert_called_once()
    assert mock_submit.call_args.kwargs["metadata"]["source"] == "web"
