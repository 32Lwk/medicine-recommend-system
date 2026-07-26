"""focus LLM — 構造的曖昧さで発動し、単語リスト拡張に依存しない。"""
from __future__ import annotations

from src.services.medicine_qa_focus_llm import (
    _looks_structurally_ambiguous,
    should_try_focus_llm_enrichment,
)


def test_general_is_ambiguous():
    assert _looks_structurally_ambiguous(
        "どうなん？",
        ["general"],
        conversation_history=[{"role": "user", "content": "頭痛"}],
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )


def test_side_effect_usage_conflict_is_ambiguous():
    assert _looks_structurally_ambiguous(
        "それ飲んだあと眠くなる？",
        ["side_effect", "usage"],
        conversation_history=[{"role": "assistant", "content": "ロキソニン推奨"}],
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )


def test_clear_single_focus_not_ambiguous_without_context():
    assert not _looks_structurally_ambiguous(
        "ロキソニンの副作用は？",
        ["side_effect"],
        conversation_history=None,
        recommended_medicines=None,
    )


def test_anaphora_short_with_context_is_ambiguous(monkeypatch):
    monkeypatch.setenv("MEDICINE_QA_FOCUS_LLM", "1")
    monkeypatch.setattr(
        "src.services.medicine_qa_focus_llm._has_openai_client",
        lambda: True,
    )
    assert should_try_focus_llm_enrichment(
        ["general"],
        "それ大丈夫？",
        conversation_history=[{"role": "assistant", "content": "イブ推奨"}],
        recommended_medicines=[{"product_name": "イブ"}],
    )
