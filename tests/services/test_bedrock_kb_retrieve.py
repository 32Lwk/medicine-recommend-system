"""bedrock_kb_retrieve.py"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("CONCIERGE_RAG_PROVIDER", raising=False)
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)


def test_retrieve_disabled_returns_empty():
    from src.services.bedrock_kb_retrieve import retrieve_concierge_context

    result = retrieve_concierge_context("Cloud Run とは")
    assert result["chunks"] == []
    assert result["provider"] == "local"


def test_retrieve_calls_bedrock(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "chunk one"},
                "location": {"s3Location": {"uri": "s3://bucket/doc.md"}},
                "score": 0.9,
            }
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        result = retrieve_concierge_context("architecture", top_k=3, use_cache=False)
    assert result["chunk_count"] == 1
    assert result["chunks"][0] == "chunk one"
    assert "s3://bucket/doc.md" in result["source_uris"]


def test_retrieve_filters_low_score_chunks(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_MIN_SCORE", "0.5")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "keep me"},
                "location": {"s3Location": {"uri": "s3://bucket/good.md"}},
                "score": 0.82,
            },
            {
                "content": {"text": "drop me"},
                "location": {"s3Location": {"uri": "s3://bucket/bad.md"}},
                "score": 0.21,
            },
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        result = retrieve_concierge_context("architecture", use_cache=False)
    assert result["chunk_count"] == 1
    assert result["chunks"] == ["keep me"]
    assert result["dropped_low_score"] == 1
