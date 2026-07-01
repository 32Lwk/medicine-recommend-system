"""Tests for pipeline end guard turn detail logging."""

from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response


def test_finalize_pipeline_schedules_detail_log_when_bot_added() -> None:
    session = {
        "messages": [
            {"type": "user", "content": "やあ"},
            {"type": "bot", "content": "こんにちは"},
        ]
    }
    with patch(
        "src.handlers.chat.chat_pipeline_end_guard._schedule_turn_detail_log"
    ) as mock_schedule:
        resp = finalize_pipeline_response(
            session,
            "sess1",
            None,
            bot_count_before=0,
            response=({"status": "ok"}, 200),
            user_message="やあ",
        )
    assert resp == ({"status": "ok"}, 200)
    mock_schedule.assert_called_once_with(session, "sess1", user_message="やあ")


def test_finalize_pipeline_fail_loud_on_missing_bot() -> None:
    session: dict = {"messages": []}
    with patch(
        "src.handlers.chat.chat_pipeline_end_guard._schedule_turn_detail_log"
    ) as mock_schedule:
        body, status = finalize_pipeline_response(
            session,
            "sess2",
            object(),
            bot_count_before=0,
            response=({"status": "ok"}, 200),
            user_message="hello",
        )
    assert status == 200
    assert body.get("pipeline_end_guard") == "missing"
    assert session["messages"] == []
    mock_schedule.assert_called_once()
