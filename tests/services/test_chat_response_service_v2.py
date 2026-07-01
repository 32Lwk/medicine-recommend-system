"""chat_response_service v2 履歴統合テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.chat_response_service import build_question_response


@patch("src.utils.structured_logger.log_medicine_question_detail")
@patch("config.llm_flags.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.history.resolve_conversation_history_with_fallback")
@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
def test_build_question_response_uses_v2_history(_line, mock_resolve, _v2, _log):
    mock_resolve.return_value = [{"type": "user", "content": "v2 qa history"}]

    def _chat(_msg, history, *_args, **_kwargs):
        assert history == [{"type": "user", "content": "v2 qa history"}]
        return {"answer": "ok"}

    session = MagicMock()
    session.get.return_value = "tester"

    build_question_response(
        "この薬の副作用は？",
        "web:U1",
        session,
        MagicMock(),
        lambda _sid: {"messages": [], "session_id": _sid},
        MagicMock(),
        _chat,
    )
    mock_resolve.assert_called_once_with(session, "web:U1", agent_kind="default", limit=10)
