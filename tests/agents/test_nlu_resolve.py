"""resolve_nlu_for_recommendation"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation


@patch("config.llm_flags.is_agent_enabled", return_value=False)
@patch("src.core.rule_based_recommendation.hybrid_nlu_extraction")
def test_legacy_hybrid_when_agent_off(mock_hybrid, _enabled):
    mock_hybrid.return_value = {"symptoms": ["headache"]}
    out = resolve_nlu_for_recommendation("頭痛", {"age": 30}, MagicMock(), session_id="s1")
    assert out["symptoms"] == ["headache"]
    mock_hybrid.assert_called_once()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch("src.agents.nlu_agent.run_nlu_agent")
def test_agent_nlu_when_present(mock_agent, _enabled):
    mock_agent.return_value = {
        "nlu": {"symptoms": ["cough"], "gender_detected": {"detected": False}},
        "source": "llm",
    }
    out = resolve_nlu_for_recommendation("咳", {}, MagicMock(), session_id="s2")
    assert out["symptoms"] == ["cough"]
    assert out.get("_nlu_agent") == "llm"
