"""花粉症・アレルギー性鼻炎時に総合感冒薬が top1 にならないこと（GC-COLD-ALL-002）"""
import pandas as pd
import pytest

from src.core.candidate_scoring import (
    get_candidate_medicines,
    has_allergic_rhinitis_efficacy,
    is_pollen_rhinitis_focus,
)
from src.core.medicine_classifiers import is_comprehensive_cold_medicine
from src.core.medicine_data import CSV_PATH
from src.core.rule_based_recommendation import (
    rule_based_medicine_recommendation,
    simple_pattern_matching_nlu,
)


@pytest.fixture(scope="module")
def medicine_df():
    return pd.read_csv(CSV_PATH)


class TestIsPollenRhinitisFocus:
    def test_pollen_season_nasal_only(self):
        text = "花粉の季節で鼻水とくしゃみがひどいです"
        symptoms = ["鼻水", "くしゃみ"]
        assert is_pollen_rhinitis_focus(text, symptoms) is True

    def test_pollen_with_throat_pain_stays_focus(self):
        """のど痛み併存でも花粉症文脈は維持（総合感冒薬 top1 バグ対策）"""
        text = "花粉症で、鼻水とくしゃみがひどいです。目もかゆくて、のども痛いです。"
        symptoms = ["鼻水", "くしゃみ", "のどの痛み"]
        assert is_pollen_rhinitis_focus(text, symptoms) is True

    def test_pollen_with_fever_not_focus(self):
        text = "花粉症ですが発熱と咳も出ています"
        symptoms = ["鼻水", "くしゃみ", "発熱", "咳"]
        assert is_pollen_rhinitis_focus(text, symptoms) is False

    def test_plain_cold_not_focus(self):
        text = "鼻水とくしゃみが出ます"
        symptoms = ["鼻水", "くしゃみ"]
        assert is_pollen_rhinitis_focus(text, symptoms) is False


class TestPollenCandidatePool:
    def test_no_cold_type_when_pollen_focus(self, medicine_df):
        user_text = "花粉の季節で鼻水とくしゃみがひどいです"
        nlu = simple_pattern_matching_nlu(user_text, {})
        cands = get_candidate_medicines(nlu, medicine_df, user_text)
        cold_type = [c for c in cands if c.get("medicine_type") == "風邪薬"]
        assert len(cold_type) == 0

    def test_has_rhinitis_efficacy_candidates(self, medicine_df):
        user_text = "花粉症で鼻水とくしゃみがひどいです"
        nlu = simple_pattern_matching_nlu(user_text, {})
        cands = get_candidate_medicines(nlu, medicine_df, user_text)
        rhinitis = [
            c
            for c in cands
            if has_allergic_rhinitis_efficacy(c.get("efficacy", ""))
        ]
        assert len(rhinitis) > 0


class TestPollenRecommendationTop3:
    @pytest.mark.parametrize(
        "user_text",
        [
            "花粉の季節で鼻水とくしゃみがひどいです",
            "花粉症で、鼻水とくしゃみがひどいです。目もかゆくて、のども痛いです。",
        ],
    )
    def test_top3_not_only_comprehensive_cold(self, user_text):
        nlu = simple_pattern_matching_nlu(user_text, {})
        result = rule_based_medicine_recommendation(
            user_text,
            {"age": 30, "allergies": ["なし"]},
            client=None,
            precomputed_nlu=nlu,
        )
        recs = result.get("recommended_medicines", [])[:3]
        assert len(recs) >= 1
        assert all(r.get("medicine_type") != "風邪薬" for r in recs), (
            "花粉症文脈で風邪薬が top3 に入っている: "
            + ", ".join(r.get("product_name", "") for r in recs)
        )
        has_rhinitis_scope = any(
            r.get("medicine_type") in ("鼻炎用薬", "抗アレルギー薬")
            or has_allergic_rhinitis_efficacy(r.get("efficacy", ""))
            for r in recs
        )
        assert has_rhinitis_scope
        only_comprehensive_cold = all(
            is_comprehensive_cold_medicine(r)
            and not has_allergic_rhinitis_efficacy(r.get("efficacy", ""))
            for r in recs
        )
        assert not only_comprehensive_cold

    def test_eye_drop_slot_when_eye_itch(self):
        user_text = "花粉症で鼻水とくしゃみ。目もかゆいです"
        nlu = simple_pattern_matching_nlu(user_text, {})
        result = rule_based_medicine_recommendation(
            user_text,
            {"age": 30, "allergies": ["なし"]},
            client=None,
            precomputed_nlu=nlu,
        )
        recs = result.get("recommended_medicines", [])[:3]
        assert any("目薬" in str(r.get("medicine_type", "")) for r in recs)

    def test_usage_notes_include_combination_when_multiple_rhinitis(self):
        user_text = "花粉症で鼻水とくしゃみがひどい。目もかゆいです"
        nlu = simple_pattern_matching_nlu(user_text, {})
        result = rule_based_medicine_recommendation(
            user_text,
            {"age": 30, "allergies": ["なし"]},
            client=None,
            precomputed_nlu=nlu,
        )
        notes = result.get("usage_notes") or ""
        if len(result.get("recommended_medicines", [])) >= 2:
            assert "併用" in notes or "点鼻" in notes or "反跳" in notes
