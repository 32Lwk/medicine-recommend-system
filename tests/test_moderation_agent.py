"""ModerationAgent"""
import json
from unittest.mock import MagicMock, patch

from src.agents.moderation_agent import run_moderation_agent, should_run_moderation
from src.agents.protocols import ModerationResult


def test_should_run_moderation_low_confidence():
    assert should_run_moderation(needs_llm_review=False, triage_result={"confidence": 0.5})


@patch("src.core.llm_client.chat_completion_create")
def test_run_moderation_agent_parses_json(mock_llm):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps({"label": "safe", "confidence": 0.9})))]
    mock_llm.return_value = mock_resp
    out = run_moderation_agent("hello", MagicMock(), trace_id="t1", sid="s1")
    assert out["label"] == "safe"
    mod = ModerationResult.from_dict(out)
    assert mod.label == "safe"
