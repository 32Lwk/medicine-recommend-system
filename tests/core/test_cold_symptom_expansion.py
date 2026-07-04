"""Tests for cold_symptom_expansion (RECO_COLD_NLU_V2)."""
from __future__ import annotations

from src.core.recommendation.cold_symptom_expansion import (
    merge_cold_symptoms,
    should_prompt_cold_symptoms,
)


def test_should_prompt_vague_cold_only():
    assert should_prompt_cold_symptoms("風邪です")


def test_should_not_prompt_cold_swim():
    assert not should_prompt_cold_symptoms(
        "風邪ですが、明日水泳の大会なので使える薬を教えて"
    )


def test_merge_expands_cold_symptoms():
    nlu = {"symptoms": [{"name": "発熱"}, {"name": "頭痛"}]}
    merged = merge_cold_symptoms(nlu, "風邪で苦しい")
    names = {s["name"] for s in merged["symptoms"]}
    assert "咳" in names
    assert "発熱" in names


def test_merge_skips_when_prompt_needed():
    nlu = {"symptoms": []}
    merged = merge_cold_symptoms(nlu, "風邪です")
    assert merged == nlu
