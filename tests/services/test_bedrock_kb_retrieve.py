"""bedrock_kb_retrieve.py"""
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
    with patch("boto3.client", return_value=mock_client):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        result = retrieve_concierge_context("architecture", top_k=3, use_cache=False)
    assert result["chunk_count"] == 1
    assert result["chunks"][0] == "chunk one"
    assert "s3://bucket/doc.md" in result["source_uris"]
