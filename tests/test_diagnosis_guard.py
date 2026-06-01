"""診断ガード（Physical 推奨可否）のユニットテスト"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.diagnosis_guard import (  # noqa: E402
    evaluate_physical_recommendation,
    merge_diagnosis_session,
    strictest_diagnosis_type,
)


class TestStrictestType:
    def test_serious_over_chronic(self):
        assert strictest_diagnosis_type(["chronic", "serious"]) == "serious"


class TestPhysicalRecommendation:
    def test_serious_blocks(self):
        d = evaluate_physical_recommendation(
            "癌ですが頭痛がします",
            {},
            {
                "diagnosis_block_types": ["serious"],
                "has_symptom": True,
                "should_show_counseling": True,
            },
        )
        assert not d.allowed
        assert d.block_code == "serious"

    def test_hypertension_headache_allowed(self):
        d = evaluate_physical_recommendation(
            "高血圧ですが頭痛がします",
            {},
            {
                "diagnosis_block_types": ["chronic"],
                "has_symptom": True,
                "selected_diagnosis": "高血圧",
            },
        )
        assert d.allowed

    def test_hypertension_pregnancy_blocked(self):
        d = evaluate_physical_recommendation(
            "高血圧で妊娠中ですが頭痛",
            {"pregnant": True},
            {"diagnosis_block_types": ["chronic"], "has_symptom": True},
        )
        assert not d.allowed

    def test_diabetes_headache_blocked(self):
        d = evaluate_physical_recommendation(
            "糖尿病ですが頭痛",
            {},
            {"diagnosis_block_types": ["chronic"], "has_symptom": True},
        )
        assert not d.allowed

    def test_heart_failure_headache_blocked(self):
        d = evaluate_physical_recommendation(
            "心不全ですが頭痛がします",
            {},
            {"diagnosis_block_types": ["chronic"], "has_symptom": True},
        )
        assert not d.allowed

    def test_insomnia_adult_allowed(self):
        d = evaluate_physical_recommendation(
            "不眠症です。市販の睡眠薬を探しています",
            {"age": 30},
            {
                "diagnosis_block_types": ["mental_health"],
                "has_symptom": True,
                "selected_diagnosis": "不眠症",
            },
        )
        assert d.allowed

    def test_insomnia_on_treatment_blocked(self):
        d = evaluate_physical_recommendation(
            "不眠症です。睡眠の薬を処方されています",
            {"age": 30},
            {
                "diagnosis_block_types": ["mental_health"],
                "has_symptom": True,
                "has_treatment": True,
            },
        )
        assert not d.allowed

    def test_pediatric_insomnia_blocked(self):
        d = evaluate_physical_recommendation(
            "不眠症です。市販の睡眠薬",
            {"age": 10},
            {"diagnosis_block_types": ["mental_health"], "has_symptom": True},
        )
        assert not d.allowed

    def test_depression_sleep_otc_blocked(self):
        d = evaluate_physical_recommendation(
            "うつ病です。市販の睡眠薬を教えてください",
            {},
            {"diagnosis_block_types": ["mental_health"], "has_symptom": True},
        )
        assert not d.allowed

    def test_merge_session_flags(self):
        session = {"user_attributes": {}}
        merge_diagnosis_session(
            session,
            "chronic",
            {"diagnosis_block_types": ["chronic", "mental_health"]},
        )
        assert session["user_attributes"]["diagnosis_session_active"] is True
        assert "chronic" in session["user_attributes"]["diagnosis_block_types"]
        assert "mental_health" in session["user_attributes"]["diagnosis_block_types"]
