"""第二段階 Other トリアージの省略テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services import llm_triage as lt


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage0b_fast_path_sets_concierge_intent(mock_budget, _drug, mock_chat):
    """第一段階省略（stage0b）でも concierge_intent を返す。"""
    result = lt.llm_triage("ありがとう", MagicMock(), use_cache=False)
    assert result["category"] == "Other"
    assert result["concierge_intent"] == "thanks"
    assert result["concierge_intent_source"] == "exact_match_gate"
    assert mock_chat.call_count == 0
    mock_budget.assert_not_called()


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_skipped_for_greeting(mock_budget, _drug, mock_chat):
    result = lt.llm_triage("こんにちは", MagicMock(), use_cache=False)
    assert result["category"] == "Other"
    assert result["concierge_intent"] == "greeting"
    assert mock_chat.call_count == 0
    mock_budget.assert_not_called()


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


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage0_session_admin_skips_all_llm(mock_budget, _drug, mock_chat):
    result = lt.llm_triage("ステータスを教えて", MagicMock(), use_cache=False)
    assert result["category"] == "Other"
    assert result["subcategory"] == "session_admin"
    assert result["session_intent"] == "status"
    assert result["concierge_intent"] == "session_ops"
    assert mock_chat.call_count == 0
    mock_budget.assert_not_called()


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage._session_admin_fast_path")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_skipped_for_session_admin_after_stage1(
    mock_budget, _drug, mock_session_path, mock_chat
):
    stage1 = (
        '{"category": "Other", "confidence": 0.99, '
        '"subcategory": "general_other", "requires_immediate_action": false, '
        '"reasoning": "other"}'
    )
    mock_session_path.side_effect = [
        None,
        {
            "category": "Other",
            "confidence": 1.0,
            "subcategory": "session_admin",
            "session_intent": "summarize",
            "concierge_intent": "session_ops",
            "concierge_intent_source": "session_keyword_probe",
        },
    ]
    mock_chat.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
    ]
    result = lt.llm_triage("履歴を要約して", MagicMock(), use_cache=False)
    assert result["subcategory"] == "session_admin"
    assert result["session_intent"] == "summarize"
    assert mock_chat.call_count == 1
