"""成分名に正規表現の記号（括弧など）が入っていても、副作用・相互作用の照合で例外にならないこと。"""
import pandas as pd
import pytest

from src.core import scoring_utils


@pytest.fixture
def side_effects_df():
    return pd.DataFrame([
        {"成分名": "ロートエキス(ハシリドコロ)", "副作用レベル": "中", "副作用症状": "口渇", "禁忌条件": "", "出典": "test"},
    ])


@pytest.fixture
def interactions_df():
    return pd.DataFrame([
        {"成分A": "ロートエキス(ハシリドコロ)", "成分B": "ワーファリン", "相互作用レベル": "高", "説明": "test", "出典": "test"},
    ])


@pytest.mark.parametrize("ingredient", ["ロートエキス(ハシリ", "成分[1", "a+b*", "ロートエキス(ハシリドコロ)"])
def test_side_effect_score_accepts_regex_metachars(monkeypatch, side_effects_df, ingredient):
    monkeypatch.setattr(scoring_utils, "load_side_effects_data", lambda: side_effects_df)
    score = scoring_utils.calculate_side_effect_risk_score({"ingredients": ingredient}, {"age": 30})
    assert -1.0 <= score <= 0.0


def test_side_effect_score_matches_literal_parenthesis(monkeypatch, side_effects_df):
    monkeypatch.setattr(scoring_utils, "load_side_effects_data", lambda: side_effects_df)
    score = scoring_utils.calculate_side_effect_risk_score({"ingredients": "ロートエキス(ハシリドコロ)"}, {"age": 30})
    assert score < 0.0


@pytest.mark.parametrize("medication", ["ワーファリン", "ワーファリン(錠", "薬[a"])
def test_interaction_checks_accept_regex_metachars(monkeypatch, interactions_df, medication):
    monkeypatch.setattr(scoring_utils, "load_interactions_data", lambda: interactions_df)
    candidate = {"ingredients": "ロートエキス(ハシリドコロ)"}
    user_info = {"age": 60, "current_medications": [medication]}
    score = scoring_utils.calculate_interaction_risk_score(candidate, user_info)
    assert -1.0 <= score <= 0.0
    has_interaction, warnings = scoring_utils.check_drug_interactions(candidate, user_info)
    assert isinstance(has_interaction, bool)
    assert isinstance(warnings, list)
