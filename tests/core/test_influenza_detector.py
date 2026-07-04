"""Tests for influenza high-fever requirement."""
from __future__ import annotations

from src.core.influenza_detector import detect_influenza_risk


def test_no_influenza_without_high_fever_three_symptoms():
    nlu = {
        "symptoms": [
            {"name": "発熱", "severity": "中等度"},
            {"name": "頭痛", "severity": "中等度"},
            {"name": "関節痛", "severity": "中等度"},
            {"name": "悪寒", "severity": "中等度"},
        ]
    }
    risk, reason = detect_influenza_risk(nlu, "風邪っぽい")
    assert risk is False
    assert reason == ""


def test_influenza_with_high_fever_and_symptoms():
    nlu = {
        "symptoms": [
            {"name": "発熱", "severity": "重度"},
            {"name": "頭痛", "severity": "中等度"},
            {"name": "関節痛", "severity": "中等度"},
        ]
    }
    risk, _ = detect_influenza_risk(nlu, "38.5度")
    assert risk is True
