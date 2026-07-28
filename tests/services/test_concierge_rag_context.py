"""Concierge Meta KB contextual retrieve クエリの unit tests。"""
from __future__ import annotations

from src.services.concierge_rag_context import (
    build_concierge_meta_contextual_query,
    extract_concierge_topic_hints,
    needs_concierge_meta_context_enrichment,
)


def test_needs_enrichment_for_follow_up():
    hist = [{"role": "user", "content": "Local RAG って何？"}]
    assert needs_concierge_meta_context_enrichment("もう少し詳しく", hist)


def test_needs_enrichment_for_short_with_history():
    hist = [{"role": "user", "content": "インフラ構成教えて"}]
    assert needs_concierge_meta_context_enrichment("詳しく", hist)


def test_extract_topic_hints_from_history():
    hist = [
        {"role": "user", "content": "CodePipeline のデプロイフローは？"},
        {"role": "assistant", "content": "…"},
    ]
    hints = extract_concierge_topic_hints(hist)
    assert any("CodePipeline" in h or "デプロイ" in h for h in hints)


def test_build_contextual_query_includes_prior_topic():
    hist = [
        {"role": "user", "content": "GCP と AWS の違いは？"},
        {"role": "assistant", "content": "GCP本番…"},
    ]
    q = build_concierge_meta_contextual_query(
        "もうちょい詳しく",
        hist,
        intent="architecture",
    )
    assert "もうちょい詳しく" in q
    assert "GCP" in q or "AWS" in q or "直前トピック" in q


def test_standalone_query_unchanged():
    q = build_concierge_meta_contextual_query(
        "Bedrock KB とは何ですか？",
        None,
        intent="architecture",
    )
    assert "Bedrock KB" in q and "とは何ですか" in q
