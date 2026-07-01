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

