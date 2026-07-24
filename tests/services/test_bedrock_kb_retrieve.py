"""bedrock_kb_retrieve.py"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("CONCIERGE_RAG_PROVIDER", raising=False)
    monkeypatch.delenv("MEDICINE_RAG_PROVIDER", raising=False)
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_MEDICINE_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_KB_SEARCH_MODE", raising=False)


def test_retrieve_disabled_returns_empty():
    from src.services.bedrock_kb_retrieve import retrieve_concierge_context

    result = retrieve_concierge_context("Cloud Run とは")
    assert result["chunks"] == []
    assert result["provider"] == "local"


def test_retrieve_calls_bedrock_managed(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_SEARCH_MODE", "managed")

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
    cfg = mock_client.retrieve.call_args.kwargs["retrievalConfiguration"]
    assert "managedSearchConfiguration" in cfg
    assert cfg["managedSearchConfiguration"]["numberOfResults"] == 3


def test_retrieve_vector_mode_for_legacy_kb(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_SEARCH_MODE", "vector")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {"retrievalResults": []}
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        retrieve_concierge_context("architecture", use_cache=False)
    cfg = mock_client.retrieve.call_args.kwargs["retrievalConfiguration"]
    assert "vectorSearchConfiguration" in cfg


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


def test_medicine_retrieve_builds_query_with_product_names(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "interaction row"},
                "location": {"s3Location": {"uri": "s3://bucket/interactions.csv"}},
                "score": 0.91,
            }
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_medicine_context

        result = retrieve_medicine_context(
            "併用できますか",
            recommended_medicines=[{"product_name": "カロナールA"}],
            use_cache=False,
        )
    assert result["chunk_count"] == 1
    query = mock_client.retrieve.call_args.kwargs["retrievalQuery"]["text"]
    assert "併用できますか" in query
    assert "カロナールA" in query


def test_augment_medicine_prompt_appends_kb_block(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
        return_value={
            "chunks": ["イブプロフェンとワーファリンは高リスク"],
            "source_uris": ["s3://bucket/interactions.csv"],
        },
    ):
        from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

        out = augment_medicine_prompt_with_kb("併用", "base prompt")
    assert "base prompt" in out
    assert "医薬品ナレッジベース参照" in out
    assert "イブプロフェン" in out
