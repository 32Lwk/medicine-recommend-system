"""推奨除外製品リスト（RECOMMENDATION_EXCLUDED_PRODUCTS）のテスト"""
import pandas as pd

from src.core.candidate_scoring import get_candidate_medicines
from src.core.medicine_classifiers import is_recommendation_excluded_product


class TestRecommendationExcludedProducts:
    def test_classifier_matches_full_and_half_width_names(self):
        assert is_recommendation_excluded_product({"product_name": "イブプロフェン錠２００Ｓ"})
        assert is_recommendation_excluded_product({"product_name": "イブプロフェン錠200S"})
        assert is_recommendation_excluded_product({"product_name": "イブプロフェン錠２００ＳＣ"})
        assert is_recommendation_excluded_product({"product_name": "イブプロフェン錠200SC"})

    def test_classifier_does_not_match_similar_products(self):
        assert not is_recommendation_excluded_product({"product_name": "トキワイブプロエースＡ"})
        assert not is_recommendation_excluded_product({"product_name": "イブA錠EX"})
        assert not is_recommendation_excluded_product({"product_name": "イブプロフェンソフトカプセル２００「キョーワ」"})

    def test_get_candidate_medicines_excludes_listed_products(self):
        medicine_df = pd.DataFrame([
            {
                "製品名": "イブプロフェン錠２００Ｓ",
                "メーカー名": "奥田製薬",
                "分類": "指定第2類",
                "医薬品の種類": "解熱鎮痛薬",
                "効能効果": "発熱、頭痛",
                "用法用量": "15歳以上",
                "年齢制限": "15",
                "成分": "イブプロフェン",
                "禁止物質あり": "",
            },
            {
                "製品名": "トキワイブプロエースＡ",
                "メーカー名": "常盤薬品工業",
                "分類": "指定第2類",
                "医薬品の種類": "解熱鎮痛薬",
                "効能効果": "発熱、頭痛",
                "用法用量": "15歳以上",
                "年齢制限": "15",
                "成分": "イブプロフェン",
                "禁止物質あり": "",
            },
        ])
        nlu_result = {"symptoms": [{"name": "発熱"}]}
        candidates = get_candidate_medicines(nlu_result, medicine_df, user_text="熱があります")
        names = [c["product_name"] for c in candidates]
        assert "イブプロフェン錠２００Ｓ" not in names
        assert "トキワイブプロエースＡ" in names
