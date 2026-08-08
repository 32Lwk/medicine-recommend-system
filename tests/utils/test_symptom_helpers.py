"""symptom_helpers の正規化テスト。"""
from __future__ import annotations

from src.utils.symptom_helpers import normalize_symptom_names


def test_normalize_symptom_names_strings() -> None:
    assert normalize_symptom_names(["頭痛", "  発熱  "]) == ["頭痛", "発熱"]


def test_normalize_symptom_names_dicts() -> None:
    raw = [{"name": "頭痛"}, {"symptom": "咳"}, {"label": "鼻水"}]
    assert normalize_symptom_names(raw) == ["頭痛", "咳", "鼻水"]


def test_normalize_symptom_names_mixed() -> None:
    raw = ["頭痛", {"name": "発熱"}, None, ""]
    assert normalize_symptom_names(raw) == ["頭痛", "発熱"]


def test_refine_nlu_symptoms_ear_pain_from_generic_inflammation() -> None:
    from src.utils.symptom_helpers import refine_nlu_symptoms_from_context

    nlu = {"symptoms": [{"name": "炎症", "severity": "軽度"}]}
    out = refine_nlu_symptoms_from_context("耳が痛い", nlu)
    names = normalize_symptom_names(out["symptoms"])
    assert "耳の痛み" in names


def test_refine_nlu_symptoms_urticaria_adds_jinmashin() -> None:
    from src.utils.symptom_helpers import refine_nlu_symptoms_from_context

    nlu = {"symptoms": [{"name": "発疹", "severity": "軽度"}]}
    out = refine_nlu_symptoms_from_context("蕁麻疹出た", nlu)
    names = normalize_symptom_names(out["symptoms"])
    assert "じんましん" in names

