"""嗜好による候補除外（confidence 閾値）"""
from src.core.recommendation.preference_candidate_filter import (
    filter_candidates_by_preferences,
)


class TestPreferenceCandidateFilter:
    def test_low_confidence_does_not_exclude(self):
        candidates = [
            {
                "product_name": "A",
                "ingredients": "クロルフェニラミン",
                "medicine_type": "鼻炎用薬",
            }
        ]
        prefs = {
            "avoid_drowsiness": True,
            "avoid_drowsiness_confidence": 0.6,
        }
        assert len(filter_candidates_by_preferences(candidates, prefs)) == 1

    def test_excludes_vasoconstrictor_nasal_when_avoid_nasal_high(self):
        candidates = [
            {
                "product_name": "ナシビン",
                "ingredients": "オキシメタゾリン",
                "usage": "点鼻",
                "medicine_type": "鼻炎用薬",
                "efficacy": "アレルギー性鼻炎",
            },
            {
                "product_name": "フルナーゼ",
                "ingredients": "フルチカゾン",
                "usage": "点鼻",
                "medicine_type": "鼻炎用薬",
                "efficacy": "アレルギー性鼻炎",
            },
        ]
        prefs = {
            "avoid_nasal_route": True,
            "avoid_nasal_route_confidence": 0.9,
        }
        out = filter_candidates_by_preferences(candidates, prefs)
        names = [c["product_name"] for c in out]
        assert "フルナーゼ" in names
        assert "ナシビン" not in names
