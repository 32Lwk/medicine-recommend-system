"""NLUAgent"""
from unittest.mock import MagicMock, patch

from src.agents.nlu_agent import run_nlu_agent


@patch("src.core.rule_based_recommendation.hybrid_nlu_extraction", return_value={"symptoms": ["頭痛"]})
def test_nlu_agent_hybrid_facade(mock_hybrid):
    out = run_nlu_agent("頭が痛いです", {"age": 30, "gender": "男性"}, MagicMock())
    assert out["source"] == "hybrid"
    assert out["nlu"]["symptoms"] == ["頭痛"]
    mock_hybrid.assert_called_once()
