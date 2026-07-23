"""personalize_ranker.py"""
from unittest.mock import MagicMock, patch

import pytest


def test_rerank_disabled_without_campaign():
    from src.services.personalize_ranker import rerank_if_enabled

    meds = [{"product_id": "a", "name": "A"}, {"product_id": "b", "name": "B"}]
    assert rerank_if_enabled(meds, session_id="sess-1") == meds


def test_rerank_reorders(monkeypatch):
    monkeypatch.setenv("PERSONALIZE_CAMPAIGN_ARN", "arn:aws:personalize:ap-northeast-1:1:campaign/x")
    mock_runtime = MagicMock()
    mock_runtime.get_personalized_ranking.return_value = {
        "personalizedRanking": [{"itemId": "b"}, {"itemId": "a"}]
    }
    with patch("boto3.client", return_value=mock_runtime):
        from src.services.personalize_ranker import rerank_if_enabled

        meds = [{"product_id": "a"}, {"product_id": "b"}]
        out = rerank_if_enabled(meds, session_id="sess-1")
    assert [m["product_id"] for m in out] == ["b", "a"]
