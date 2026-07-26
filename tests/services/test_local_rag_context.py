"""local_rag_context — 会話文脈から retrieve クエリ合成。"""
from __future__ import annotations

from src.services.local_rag_context import (
    build_contextual_retrieval_query,
    extract_context_substances,
    needs_context_enrichment,
)


def test_extract_substances_from_history() -> None:
    history = [
        {"role": "user", "content": "ロキソニンを飲んでいます"},
        {"role": "assistant", "content": "承知しました"},
    ]
    subs = extract_context_substances(history)
    assert "ロキソニン" in subs or "ロキソプロフェン" in subs


def test_anaphora_needs_enrichment() -> None:
    history = [
        {"role": "user", "content": "ワーファリンを処方されています"},
    ]
    assert needs_context_enrichment("それ一緒に飲んでいい？", history)


def test_build_contextual_query_merges_drugs() -> None:
    history = [
        {"role": "user", "content": "ロキソニンを服用中です"},
        {"role": "assistant", "content": "了解"},
        {"role": "user", "content": "ワーファリンも処方されているんですが、それ一緒に大丈夫？"},
    ]
    q = "ワーファリンも処方されているんですが、それ一緒に大丈夫？"
    built = build_contextual_retrieval_query(q, history)
    assert "ロキソ" in built or "ロキソプロフェン" in built
    assert "ワーファリン" in built
