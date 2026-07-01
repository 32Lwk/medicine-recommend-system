"""line_memory_context v2 委譲テスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.line_memory_context import get_counseling_conversation_history


@patch("config.llm_flags.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.history.resolve_counseling_history_with_fallback")
def test_get_counseling_history_delegates_to_v2(mock_resolve, _v2):
    mock_resolve.return_value = [{"type": "user", "content": "v2 history"}]
    out = get_counseling_conversation_history({}, "line:U1")
    assert out == [{"type": "user", "content": "v2 history"}]
    mock_resolve.assert_called_once_with({}, "line:U1")
