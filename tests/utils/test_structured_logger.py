"""Tests for structured_logger app.log output format."""

from __future__ import annotations

import json
import logging

from src.utils.structured_logger import log_counseling_detail


def test_log_counseling_detail_emits_single_line_json(caplog) -> None:
    caplog.set_level(logging.INFO, logger="src.utils.structured_logger")

    log_counseling_detail(
        session_id="sess1",
        user_input="頭が痛い",
        response="お大事に。",
        conversation_history=[{"type": "user", "content": "頭が痛い"}],
        async_log=False,
    )

    assert len(caplog.records) == 1
    message = caplog.records[0].message
    lines = message.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("[INFO]")
    payload = json.loads(lines[1])
    assert payload["log_type"] == "counseling_detail"
    assert payload["response"] == "お大事に。"
    assert "\n" not in lines[1]
