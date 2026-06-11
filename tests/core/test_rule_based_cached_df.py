"""rule_based_medicine_recommendation が CSV を毎回読み直さないこと"""
from unittest.mock import MagicMock, patch

import pandas as pd


@patch("src.core.rule_based_recommendation.rule_based_recommendation")
@patch("src.core.rule_based_recommendation.pd.read_csv")
def test_rule_based_uses_cached_df(mock_read_csv, mock_inner):
    import src.core.medicine_data as medicine_data
    from src.core.rule_based_recommendation import rule_based_medicine_recommendation

    cached = pd.DataFrame([{"product_name": "テスト薬"}])
    medicine_data.df = cached
    mock_inner.return_value = {"status": "ok", "recommended_medicines": []}
    client = MagicMock()

    calls_before = mock_read_csv.call_count
    rule_based_medicine_recommendation("頭痛", {}, client, session_id="s1")

    assert mock_read_csv.call_count == calls_before
    mock_inner.assert_called_once()
    assert mock_inner.call_args.kwargs["medicine_df"] is cached
