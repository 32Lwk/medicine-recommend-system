"""1 POST あたり triage 呼び出し回数"""
from unittest.mock import MagicMock, patch


@patch("src.agents.triage_agent.run_triage_agent", return_value={"category": "Physical", "confidence": 0.9})
@patch("src.services.triage_analytics.log_triage_result")
def test_run_triage_calls_agent_once(_log, mock_agent):
    from src.handlers.chat.chat_triage import run_triage

    session = {"messages": [], "user_attributes": {}}
    run_triage(session, MagicMock(), "sid", "頭痛", "頭痛", MagicMock())
    assert mock_agent.call_count == 1
