"""store_inquiry_handler.retry_first_stage_with_modified_prompt の修正テスト"""
from unittest.mock import MagicMock, patch

from src.services.store_inquiry_handler import retry_first_stage_with_modified_prompt


@patch("src.services.llm_triage.llm_triage")
def test_retry_delegates_to_llm_triage(mock_llm_triage):
    mock_llm_triage.return_value = {
        "category": "Other",
        "confidence": 0.8,
        "subcategory": "store_inquiry",
    }
    client = MagicMock()
    result = retry_first_stage_with_modified_prompt("トイレはどこ", client)

    assert result["subcategory"] == "store_inquiry"
    mock_llm_triage.assert_called_once_with("トイレはどこ", client, use_cache=False)
