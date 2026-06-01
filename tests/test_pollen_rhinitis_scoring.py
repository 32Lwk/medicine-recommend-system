"""花粉症スコアリング・嗜好・点鼻注意のユニットテスト"""
import pandas as pd
import pytest

from src.core.recommendation.pollen_rhinitis_scoring import (
    VASOCONSTRICTOR_NASAL_WARNING_HTML,
    append_vasoconstrictor_nasal_warning,
    classify_pollen_rhinitis_product,
    apply_pollen_candidate_adjustments,
)
from src.core.rule_based_recommendation import (
    rule_based_medicine_recommendation,
    simple_pattern_matching_nlu,
)
from src.core.recommendation.pollen_combination_advice import build_pollen_combination_advice
from src.core.preference_merge import merge_user_preferences
from src.core.user_detection import extract_user_preferences, preference_context_text
from src.core.medicine_data import CSV_PATH


def _pattern_nlu_with_merged_prefs(user_text: str, attrs=None, **llm_fields):
    """統合テスト用: pattern NLU + 嗜好マージ結果を precomputed_nlu に載せる"""
    nlu = simple_pattern_matching_nlu(user_text, attrs or {})
    llm = {
        k: {"value": v, "confidence": 0.85, "evidence": user_text}
        for k, v in llm_fields.items()
    }
    nlu["user_preferences"] = merge_user_preferences(llm, user_text, None)
    return nlu


class TestClassifyPollenProduct:
    def test_oral_second_gen(self):
        c = {
            "product_name": "アレグラ",
            "ingredients": "フェキソフェナジン塩酸塩",
            "efficacy": "アレルギー性鼻炎",
            "medicine_type": "鼻炎用薬",
        }
        assert classify_pollen_rhinitis_product(c) == "oral_2nd_gen"

    def test_nasal_vasoconstrictor(self):
        c = {
            "product_name": "ナシビンＭスプレー",
            "ingredients": "オキシメタゾリン塩酸塩",
            "efficacy": "鼻づまり",
            "medicine_type": "鼻炎用薬",
            "usage": "点鼻",
        }
        assert classify_pollen_rhinitis_product(c) == "nasal_vasoconstrictor"


def _nlu_with_prefs(prefs: dict):
    return {"user_preferences": prefs}


class TestUserPreferences:
    def test_avoid_drowsiness_safety_keyword(self):
        p = extract_user_preferences("花粉症で運転もします。", {})
        assert p["avoid_drowsiness"] is True

    def test_prefer_nasal_from_nlu_result(self):
        p = extract_user_preferences(
            "花粉症で点鼻がいいです",
            _nlu_with_prefs(
                {"prefer_nasal_route": True, "prefer_nasal_route_confidence": 0.85}
            ),
        )
        assert p["prefer_nasal_route"] is True

    def test_reads_merged_prefs_from_nlu(self):
        text = preference_context_text(
            "花粉症で鼻水がひどい",
            {"other_info": "眠気が心配です"},
        )
        p = extract_user_preferences(
            text,
            _nlu_with_prefs(
                {"avoid_drowsiness": True, "avoid_drowsiness_confidence": 0.75}
            ),
        )
        assert p["avoid_drowsiness"] is True

    def test_dry_mouth_not_from_symptom_only(self):
        p = extract_user_preferences(
            "花粉症です",
            {"symptoms": [{"name": "口渇", "severity": "中等度"}]},
        )
        assert p["avoid_dry_mouth"] is False

    def test_dry_mouth_from_llm_prefs(self):
        p = extract_user_preferences(
            "花粉症です",
            _nlu_with_prefs({"avoid_dry_mouth": True, "avoid_dry_mouth_confidence": 0.7}),
        )
        assert p["avoid_dry_mouth"] is True


class TestPollenRankingWithPreferences:
    @pytest.fixture(scope="class")
    def medicine_df(self):
        return pd.read_csv(CSV_PATH)

    def test_avoid_drowsiness_prefers_second_gen(self, medicine_df):
        user_text = "花粉症で鼻水とくしゃみ。眠気が出る薬は避けたいです"
        nlu = _pattern_nlu_with_merged_prefs(user_text, avoid_drowsiness=True)
        prefs = extract_user_preferences(user_text, nlu)
        assert prefs["avoid_drowsiness"]
        result = rule_based_medicine_recommendation(
            user_text,
            {"age": 30, "allergies": ["なし"], "user_preferences": prefs},
            client=None,
            precomputed_nlu=nlu,
        )
        top = result["recommended_medicines"][0]
        ing = str(top.get("ingredients", ""))
        assert "フェキソフェナジン" in ing or "ロラタジン" in ing or "エバスチン" in ing

    def test_congestion_not_only_vasoconstrictor_when_sneeze_also(self):
        user_text = "花粉症で鼻づまりとくしゃみがひどい。眠気は避けたい"
        nlu = _pattern_nlu_with_merged_prefs(user_text, avoid_drowsiness=True)
        result = rule_based_medicine_recommendation(
            user_text,
            {
                "age": 30,
                "allergies": ["なし"],
                "user_preferences": extract_user_preferences(user_text, nlu),
            },
            client=None,
            precomputed_nlu=nlu,
        )
        tops = result["recommended_medicines"][:3]
        only_vaso = all(
            "オキシメタゾリン" in str(m.get("ingredients", ""))
            and "フェキソフェナジン" not in str(m.get("ingredients", ""))
            and "ロラタジン" not in str(m.get("ingredients", ""))
            for m in tops
        )
        assert not only_vaso


class TestPollenCombinationAdvice:
    def test_warns_duplicate_oral_antihistamine(self):
        recs = [
            {
                "product_name": "A",
                "pollen_product_class": "oral_2nd_gen",
                "ingredients": "フェキソフェナジン",
                "medicine_type": "鼻炎用薬",
            },
            {
                "product_name": "B",
                "pollen_product_class": "oral_2nd_gen",
                "ingredients": "ロラタジン",
                "medicine_type": "鼻炎用薬",
            },
        ]
        html = build_pollen_combination_advice(recs)
        assert "2種類" in html or "同時" in html

    def test_steroid_and_oral_ok_note(self):
        recs = [
            {
                "product_name": "フルナーゼ",
                "pollen_product_class": "nasal_steroid_allergy",
                "ingredients": "フルチカゾン",
                "medicine_type": "鼻炎用薬",
            },
            {
                "product_name": "アレグラ",
                "pollen_product_class": "oral_2nd_gen",
                "ingredients": "フェキソフェナジン",
                "medicine_type": "鼻炎用薬",
            },
        ]
        html = build_pollen_combination_advice(recs)
        assert "ステロイド点鼻" in html


class TestVasoconstrictorWarning:
    def test_append_warning(self):
        med = {
            "product_name": "ナシビン",
            "ingredients": "オキシメタゾリン塩酸塩",
            "usage": "点鼻",
            "medicine_type": "鼻炎用薬",
        }
        apply_pollen_candidate_adjustments(
            med, focus_pollen=True, symptom_names=["鼻づまり"], user_preferences={}
        )
        assert med.get("has_vasoconstrictor_nasal")
        out = append_vasoconstrictor_nasal_warning("用法に従ってください。", med)
        assert "反跳" in out
        assert VASOCONSTRICTOR_NASAL_WARNING_HTML[:20] in out
