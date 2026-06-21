"""第二段階 Other トリアージへの会話履歴付与テスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services import llm_triage as lt


@patch("src.core.llm_client.chat_completion_create")
@patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None)
@patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None))
def test_stage2_includes_conversation_history(_budget, _drug, mock_chat):
    stage1 = (
        '{"category": "Other", "confidence": 0.99, '
        '"subcategory": "general_other", "requires_immediate_action": false, '
        '"reasoning": "follow-up"}'
    )
    stage2 = (
        '{"subcategory": "store_inquiry/inventory", "confidence": 0.9, '
        '"reasoning": "inventory follow-up"}'
    )
    mock_chat.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content=stage2))]),
    ]
    history = [
        {"role": "user", "content": "風邪薬の在庫を確認したい"},
        {"role": "assistant", "content": "どの商品をお探しですか？"},
    ]
    result = lt.llm_triage(
        "ありますか",
        MagicMock(),
        use_cache=False,
        conversation_history=history,
    )
    assert "store_inquiry" in result["subcategory"]
    assert mock_chat.call_count == 2
    stage2_user_content = mock_chat.call_args_list[1][1]["messages"][1]["content"]
    assert "【直近の会話履歴】" in stage2_user_content
    assert "風邪薬" in stage2_user_content


def test_second_stage_prompt_has_ambiguous_facility_rule():
    assert "曖昧施設" in lt.SECOND_STAGE_OTHER_PROMPT
    assert "大学はどこ" in lt.SECOND_STAGE_OTHER_PROMPT


def test_first_stage_prompt_has_short_symptom_rule():
    assert "短い症状入力" in lt.FIRST_STAGE_TRIAGE_PROMPT
