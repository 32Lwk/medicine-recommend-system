"""NLUAgent"""
from unittest.mock import MagicMock, patch

from src.agents.nlu_agent import run_nlu_agent


def test_nlu_agent_rule_skip_llm():
    user_info = {"age": 30, "gender": "男性", "symptoms": ["頭痛"]}
    out = run_nlu_agent("頭が痛いです", user_info, MagicMock())
    assert out["skipped_llm"] is True
    assert out["source"] == "rule"


@patch("src.core.nlu_service.hybrid_nlu_extraction", return_value={"symptoms": []})
def test_nlu_agent_llm_fallback(mock_nlu):
    out = run_nlu_agent("頭痛", {"age": 20}, MagicMock())
    assert out["source"] == "llm"
    mock_nlu.assert_called_once()
