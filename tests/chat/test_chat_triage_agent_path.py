"""Triage agent path"""
from unittest.mock import MagicMock, patch


@patch("src.agents.triage_agent.run_triage_agent", return_value={"category": "Physical", "confidence": 0.9})
@patch("src.services.triage_analytics.log_triage_result")
def test_run_triage_uses_agent(_log, mock_agent):
    from src.handlers.chat.chat_triage import run_triage

    session = {"messages": [], "user_attributes": {}}
    early, triage = run_triage(session, MagicMock(), "sid", "頭痛", "頭痛", MagicMock())
    mock_agent.assert_called_once()
    assert triage["category"] == "Physical"
