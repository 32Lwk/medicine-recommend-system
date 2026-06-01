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
from src.core.user_detection import extract_user_preferences, preference_context_text
from src.core.medicine_data import CSV_PATH


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


class TestUserPreferences:
    def test_avoid_drowsiness_keywords(self):
        p = extract_user_preferences("花粉症で眠気が心配です。運転もします。", {})
        assert p["avoid_drowsiness"] is True

    def test_prefer_nasal(self):
        p = extract_user_preferences("花粉症で点鼻がいいです", {})
        assert p["prefer_nasal_route"] is True

    def test_other_info_from_attributes(self):
        text = preference_context_text(
            "花粉症で鼻水がひどい",
            {"other_info": "眠気が心配です"},
        )
        p = extract_user_preferences(text, {})
        assert p["avoid_drowsiness"] is True

    def test_dry_mouth_from_nlu_symptom(self):
        p = extract_user_preferences(
            "花粉症です",
            {"symptoms": [{"name": "口渇", "severity": "中等度"}]},
        )
        assert p["avoid_dry_mouth"] is True

    @pytest.mark.parametrize(
        "text",
        [
            "口が渇きにくい花粉症薬を探しています",
            "のどの渇きの少ない薬がいい",
            "喉の渇きが少ない鼻炎薬",
            "口渇の少ない抗ヒスタミン",
        ],
    )
    def test_avoid_dry_mouth_phrasing(self, text):
        assert extract_user_preferences(text, {})["avoid_dry_mouth"] is True


class TestPollenRankingWithPreferences:
    @pytest.fixture(scope="class")
    def medicine_df(self):
        return pd.read_csv(CSV_PATH)

    def test_avoid_drowsiness_prefers_second_gen(self, medicine_df):
        user_text = "花粉症で鼻水とくしゃみ。眠気が出る薬は避けたいです"
        nlu = simple_pattern_matching_nlu(user_text, {})
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
        nlu = simple_pattern_matching_nlu(user_text, {})
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
