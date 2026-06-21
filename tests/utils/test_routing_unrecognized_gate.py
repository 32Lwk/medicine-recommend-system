"""トリアージ尊重型の症状不明ゲート"""
from src.utils.input_helpers import (
    reroute_symptom_general_other_to_physical,
    should_apply_unrecognized_symptom_gate,
    should_fallback_to_symptom_recommendation,
)


def test_high_confidence_general_other_skips_unrecognized_gate():
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.99}
    assert should_apply_unrecognized_symptom_gate(triage, "はお") is False
    assert should_fallback_to_symptom_recommendation(triage) is False


def test_high_confidence_general_other_with_symptom_applies_gate():
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.99}
    assert should_apply_unrecognized_symptom_gate(triage, "頭が痛い") is True
    assert should_fallback_to_symptom_recommendation(triage, "頭が痛い") is True


def test_reroute_symptom_general_other_to_physical():
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.95}
    category, updated = reroute_symptom_general_other_to_physical(triage, "頭が痛い")
    assert category == "Physical"
    assert updated["_symptom_general_other_override"] is True


def test_low_confidence_general_other_still_applies_gate_for_g():
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.3}
    assert should_apply_unrecognized_symptom_gate(triage, "g") is True


def test_physical_category_applies_gate():
    triage = {"category": "Physical", "subcategory": "headache", "confidence": 0.9}
    assert should_apply_unrecognized_symptom_gate(triage, "g") is True
    assert should_fallback_to_symptom_recommendation(triage) is True
