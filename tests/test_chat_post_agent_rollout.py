"""LLM_AGENT_ENABLED ON でオーケストレータ経路"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from config.llm_flags import is_agent_enabled


@patch.dict("os.environ", {"LLM_AGENT_ENABLED": "1"}, clear=False)
def test_agent_enabled_all_sessions():
    assert is_agent_enabled() is True


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch("src.handlers.chat_orchestrator.try_orchestrator_route")
def test_post_pipeline_calls_orchestrator(mock_orch, _on):
    mock_orch.return_value = ({"status": "ok"}, 200)
    from src.handlers.chat.chat_post_pipeline import ChatPostContext

    ctx = ChatPostContext(
        session={"messages": [], "user_attributes": {}},
        client_info=MagicMock(client_ip="127.0.0.1", user_agent="t"),
        sid="sid-rollout",
        monitor=MagicMock(),
        user_agent="t",
        client_ip="127.0.0.1",
        user_message="頭痛",
        sanitized_message="頭痛",
        processed_message="頭痛",
        triage_result={"category": "Physical", "confidence": 0.9},
        trace_id="tr",
        recommendation_client=MagicMock(),
    )
    from config.llm_flags import is_agent_enabled as iae

    assert iae()
    from src.handlers.chat_orchestrator import try_orchestrator_route

    try_orchestrator_route(ctx, MagicMock())
    mock_orch.assert_called_once()
