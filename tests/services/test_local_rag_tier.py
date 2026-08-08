"""local_rag_context.resolve_rag_tier — Tier0/1/2 分類。"""
from __future__ import annotations


def test_resolve_rag_tier_tier0_explicit_brand():
    from src.services.local_rag_context import resolve_rag_tier

    tier = resolve_rag_tier("ロキソニンの副作用は？")
    assert tier == "tier0"


def test_resolve_rag_tier_tier1_anaphora():
    from src.services.local_rag_context import resolve_rag_tier

    hist = [
        {"type": "user", "content": "今ロキソニン飲んでます"},
        {"type": "bot", "content": "了解しました"},
    ]
    tier = resolve_rag_tier("それと一緒に飲んでも大丈夫？", conversation_history=hist)
    assert tier == "tier1"


def test_resolve_rag_tier_tier2_comparison():
    from src.services.local_rag_context import resolve_rag_tier

    recs = [
        {"product_name": "イブ"},
        {"product_name": "バファリンEX"},
    ]
    tier = resolve_rag_tier(
        "どっちがいい？",
        conversation_history=[{"type": "user", "content": "頭痛い"}],
        recommended_medicines=recs,
    )
    assert tier == "tier2"


def test_rag_tier_retrieve_params():
    from src.services.local_rag_context import rag_tier_retrieve_params

    t0 = rag_tier_retrieve_params("tier0")
    assert t0["top_k"] == 3
    assert t0["use_llm_rewrite"] is False
    t2 = rag_tier_retrieve_params("tier2")
    assert t2["force_multi_doc"] is True
