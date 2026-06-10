"""第二段階 Other トリアージの省略テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services import llm_triage as lt


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_skipped_for_greeting(mock_budget, _drug, mock_chat):
    mock_chat.return_value = MagicMock(
      choices=[
          MagicMock(
              message=MagicMock(
                  content=(
                      '{"category": "Other", "confidence": 0.99, '
                      '"subcategory": "general_other", "requires_immediate_action": false, '
                      '"reasoning": "greeting"}'
                  )
              )
          )
      ]
    )
    result = lt.llm_triage("こんにちは", MagicMock(), use_cache=False)
    assert result["category"] == "Other"
    assert result["concierge_intent"] == "greeting"
    assert mock_chat.call_count == 1


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_runs_for_ambiguous_other(mock_budget, _drug, mock_chat):
    stage1 = (
      '{"category": "Other", "confidence": 0.99, '
      '"subcategory": "general_other", "requires_immediate_action": false, '
      '"reasoning": "ambiguous"}'
    )
    stage2 = (
        '{"subcategory": "store_inquiry", "confidence": 0.9, "reasoning": "store"}'
    )
    mock_chat.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage2))]),
    ]
    result = lt.llm_triage("トイレはどこですか", MagicMock(), use_cache=False)
    assert "store_inquiry" in result["subcategory"]
    assert mock_chat.call_count == 2
