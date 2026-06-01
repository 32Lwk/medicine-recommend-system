"""嗜好マージ・安全強制・候補除外の単体テスト"""
import pytest

from src.core.preference_merge import (
    apply_safety_preference_overrides,
    merge_user_preferences,
    build_user_preferences_summary,
)
from src.core.recommendation.preference_candidate_filter import filter_candidates_by_preferences


class TestMergeUserPreferences:
    def test_safety_driving_forces_avoid_drowsiness(self):
        prefs = merge_user_preferences({}, "花粉症です。運転もします。", None)
        assert prefs["avoid_drowsiness"] is True
        assert prefs.get("field_sources", {}).get("avoid_drowsiness") == "safety"

    def test_llm_confidence_threshold(self):
        llm = {
            "avoid_dry_mouth": {"value": True, "confidence": 0.6, "evidence": "口渇が少ない"},
            "avoid_drowsiness": {"value": True, "confidence": 0.3, "evidence": "眠気"},
        }
        prefs = merge_user_preferences(llm, "テスト", None)
        assert prefs["avoid_dry_mouth"] is True
        assert prefs["avoid_drowsiness"] is False

    def test_kampo_conflict_not_wins(self):
        llm = {
            "prefers_kampo": {"value": True, "confidence": 0.9, "evidence": None},
            "prefers_not_kampo": {"value": True, "confidence": 0.8, "evidence": None},
        }
        prefs = merge_user_preferences(llm, "", None)
        assert prefs["prefers_not_kampo"] is True
        assert prefs["prefers_kampo"] is False

    def test_summary(self):
        prefs = merge_user_preferences(
            {"avoid_drowsiness": {"value": True, "confidence": 0.9, "evidence": "運転"}},
            "運転します",
            None,
        )
        summary = build_user_preferences_summary(prefs)
        assert summary["avoid_drowsiness"] is True
        assert summary["avoid_drowsiness_confidence"] >= 0.8


class TestPreferenceCandidateFilter:
    def test_excludes_first_gen_when_avoid_drowsiness_high_conf(self):
        candidates = [
            {
                "product_name": "テストA",
                "ingredients": "クロルフェニラミン",
                "medicine_type": "鼻炎用薬",
                "efficacy": "アレルギー性鼻炎",
                "final_score": 0.9,
            },
            {
                "product_name": "テストB",
                "ingredients": "フェキソフェナジン",
                "medicine_type": "鼻炎用薬",
                "efficacy": "アレルギー性鼻炎",
                "final_score": 0.8,
            },
        ]
        prefs = {
            "avoid_drowsiness": True,
            "avoid_drowsiness_confidence": 0.85,
        }
        out = filter_candidates_by_preferences(candidates, prefs)
        assert len(out) == 1
        assert "フェキソフェナジン" in out[0]["ingredients"]
