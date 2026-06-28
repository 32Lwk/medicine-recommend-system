"""counseling_detail が Cloud Run 向けに同期 stdout へ出ることのテスト。"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

from src.utils.structured_logger import log_counseling_detail


def test_log_counseling_detail_async_still_emits_app_log_sync(caplog) -> None:
    caplog.set_level(logging.INFO, logger="src.utils.structured_logger")

    with patch("src.utils.structured_logger._detail_log_executor") as mock_executor:
        log_counseling_detail(
            session_id="sess-cloud",
            user_input="こんにちは",
            response="いらっしゃいませ",
            async_log=True,
        )
        mock_executor.submit.assert_called_once()

    assert len(caplog.records) == 1
    lines = caplog.records[0].message.splitlines()
    payload = json.loads(lines[1])
    assert payload["log_type"] == "counseling_detail"
    assert payload["response"] == "いらっしゃいませ"
