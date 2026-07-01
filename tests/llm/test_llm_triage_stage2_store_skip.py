"""stage1 store 高信頼時の stage2 スキップテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services import llm_triage as lt


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_skipped_for_high_confidence_store_inquiry(mock_budget, _drug, mock_chat):
    stage1 = (
        '{"category": "Other", "confidence": 0.95, '
        '"subcategory": "store_inquiry_locator", "requires_immediate_action": false, '
        '"reasoning": "store location"}'
    )
    mock_chat.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
    ]
    result = lt.llm_triage("マツキヨは近くにありますか", MagicMock(), use_cache=False)
    assert "store_inquiry" in result["subcategory"]
    assert mock_chat.call_count == 1


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_runs_for_low_confidence_store(mock_budget, _drug, mock_chat):
    stage1 = (
        '{"category": "Other", "confidence": 0.6, '
        '"subcategory": "store_inquiry", "requires_immediate_action": false, '
        '"reasoning": "uncertain store"}'
    )
    stage2 = (
        '{"subcategory": "store_inquiry_facilities", "confidence": 0.9, "reasoning": "facilities"}'
    )
    mock_chat.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage2))]),
    ]
    result = lt.llm_triage("薬局どこ", MagicMock(), use_cache=False)
    assert mock_chat.call_count == 2
    assert "store_inquiry" in result["subcategory"]
