"""Tests for medicine_type_resolver."""
from __future__ import annotations

from src.core.recommendation.medicine_type_resolver import resolve_medicine_type_from_hints


def test_resolve_wind_cold_medicine_hint():
    assert resolve_medicine_type_from_hints("風邪薬を教えて", {}) == "風邪薬"


def test_resolve_from_analysis_result():
    assert (
        resolve_medicine_type_from_hints("頭痛", {"medicine_type": "解熱鎮痛薬"})
        == "解熱鎮痛薬"
    )


def test_resolve_none_when_unknown():
    assert resolve_medicine_type_from_hints("こんにちは", {"medicine_type": "その他"}) is None
