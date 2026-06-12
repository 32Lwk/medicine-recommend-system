"""budget_guard のリクエスト内キャッシュテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.budget_guard import check_llm_allowed, reset_budget_check_cache


@patch("src.services.budget_guard.is_llm_blocked", return_value=False)
def test_check_llm_allowed_cached_per_request(mock_blocked):
    reset_budget_check_cache()
    assert check_llm_allowed() == (True, None)
    assert check_llm_allowed() == (True, None)
    mock_blocked.assert_called_once()
