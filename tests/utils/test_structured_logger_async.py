"""Tests for async counseling_detail logging."""

from __future__ import annotations

import time
from unittest.mock import patch

from src.utils.structured_logger import log_counseling_detail


def test_log_counseling_detail_async_submits_without_blocking() -> None:
    with patch("src.utils.structured_logger._detail_log_executor") as mock_executor:
        log_counseling_detail(
            session_id="sess-async",
            user_input="test",
            response="reply",
            async_log=True,
        )
        mock_executor.submit.assert_called_once()
        payload = mock_executor.submit.call_args[0][1]
        assert payload["log_type"] == "counseling_detail"
        assert payload["response"] == "reply"


def test_emit_counseling_detail_writes_jsonl(tmp_path, monkeypatch) -> None:
    import src.utils.structured_logger as sl

    monkeypatch.setattr(sl, "LOG_DIR", str(tmp_path))
    sl._emit_counseling_detail(
        {
            "log_type": "counseling_detail",
            "timestamp": "2026-01-01T00:00:00",
            "session_id": "s1",
            "user_input": "hi",
            "response": "hello",
            "conversation_history": [],
        }
    )
    content = (tmp_path / "counseling_detail_log.jsonl").read_text(encoding="utf-8")
    assert '"response":"hello"' in content.replace(" ", "")
