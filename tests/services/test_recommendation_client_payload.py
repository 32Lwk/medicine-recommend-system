"""recommendation_client_payload のテスト。"""
from __future__ import annotations

from src.services.recommendation_client_payload import (
    enrich_recommended_medicines,
    is_sage_web_ui,
)


def test_is_sage_web_ui_from_session():
    session = {"ui_variant": "sage"}
    assert is_sage_web_ui(session) is True
    assert is_sage_web_ui({"ui_variant": "legacy"}) is False


def test_is_sage_web_ui_default():
    assert is_sage_web_ui(None) is True
    assert is_sage_web_ui({}) is True


def test_enrich_adds_symptoms_and_breakdown():
    meds = [{"product_name": "A", "scores": {"symptom": 80}}]
    out = enrich_recommended_medicines(
        meds, medicine_type="解熱鎮痛剤", symptoms=["頭痛", "発熱"]
    )
    assert out[0]["medicine_type"] == "解熱鎮痛剤"
    assert out[0]["symptoms"] == ["頭痛", "発熱"]
    assert out[0]["score_breakdown"]["symptom"] == 80
