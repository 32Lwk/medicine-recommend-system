"""Tests for diagnosis field-level i18n."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.services.diagnosis_i18n import translate_diagnosis_fields


def test_translate_diagnosis_fields_ja_passthrough():
    diag = {"render": "sage_reco", "personalized_advice": "用法を守ってください。"}
    out = translate_diagnosis_fields(diag, "ja", MagicMock())
    assert out is diag


def test_translate_diagnosis_fields_sage_reco(monkeypatch):
    diag = {
        "render": "sage_reco",
        "personalized_advice": "用法を守ってください。",
        "doctor_consultation": "医師に相談してください。",
    }

    def _translate(text, lang, client, session_id=None):
        return {"用法を守ってください。": "Follow dosage.", "医師に相談してください。": "See a doctor."}.get(text, text)

    monkeypatch.setattr(
        "src.core.translation_service.translate_medicine_recommendation",
        _translate,
    )
    out = translate_diagnosis_fields(diag, "en", MagicMock(), session_id="s1")
    assert out["i18n"]["en"]["personalized_advice"] == "Follow dosage."
    assert out["i18n"]["en"]["doctor_consultation"] == "See a doctor."


def test_translate_diagnosis_fields_sage_status(monkeypatch):
    diag = {
        "render": "sage_status",
        "title": "店舗案内",
        "message": "スタッフにお尋ねください。",
        "hints": ["2階にございます。"],
    }

    def _translate(text, lang, client, session_id=None):
        return {
            "店舗案内": "Store info",
            "スタッフにお尋ねください。": "Ask staff.",
            "2階にございます。": "On the 2nd floor.",
        }.get(text, text)

    monkeypatch.setattr(
        "src.core.translation_service.translate_medicine_recommendation",
        _translate,
    )
    out = translate_diagnosis_fields(diag, "en", MagicMock())
    assert out["i18n"]["en"]["title"] == "Store info"
    assert out["i18n"]["en"]["message"] == "Ask staff."
    assert out["i18n"]["en"]["hints"][0] == "On the 2nd floor."
