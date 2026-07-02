"""Phase 3 (p3-headache-reco): 低リスク頭痛 OTC / めまい保留テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.recommendation.low_risk_symptoms import (
    is_caution_defer_single_symptom,
    is_low_risk_headache_only,
)
from src.core.rule_based_recommendation import rule_based_medicine_recommendation
from src.handlers.chat.chat_recommendation_flow import _filter_medicines_when_age_unknown


@pytest.fixture
def headache_flag_on(monkeypatch):
    monkeypatch.setenv("RECO_LOW_RISK_HEADACHE", "true")


@pytest.fixture
def headache_flag_off(monkeypatch):
    monkeypatch.setenv("RECO_LOW_RISK_HEADACHE", "false")


def test_low_risk_headache_detection():
    nlu = {"symptoms": [{"name": "頭痛"}]}
    assert is_low_risk_headache_only(nlu, "頭痛い")
    assert not is_low_risk_headache_only(nlu, "激しい頭痛です")
    assert not is_low_risk_headache_only(
        nlu, "子どもが頭痛い", user_info={}
    )
    assert not is_low_risk_headache_only(
        {"symptoms": [{"name": "めまい"}]}, "めまいがする"
    )


def test_caution_defer_dizziness_only():
    assert is_caution_defer_single_symptom({"symptoms": [{"name": "めまい"}]})
    assert not is_caution_defer_single_symptom({"symptoms": [{"name": "頭痛"}]})


def test_filter_keeps_major_analgesics_for_headache_flag_on(headache_flag_on):
    meds = [
        {
            "product_name": "カロナールＡ",
            "medicine_type": "解熱鎮痛薬",
            "age_restriction": "15歳以上",
        },
        {
            "product_name": "小児用A",
            "medicine_type": "解熱鎮痛薬",
            "age_restriction": "7歳以上",
        },
    ]
    nlu = {"symptoms": [{"name": "頭痛"}]}
    filtered = _filter_medicines_when_age_unknown(
        meds, {}, nlu_result=nlu, user_text="頭痛い"
    )
    assert any(m["product_name"] == "カロナールＡ" for m in filtered)
    assert any(m["product_name"] == "小児用A" for m in filtered)


def test_filter_unchanged_when_flag_off(headache_flag_off):
    meds = [
        {
            "product_name": "カロナールＡ",
            "medicine_type": "解熱鎮痛薬",
            "age_restriction": "15歳以上",
        },
        {
            "product_name": "小児用A",
            "medicine_type": "解熱鎮痛薬",
            "age_restriction": "7歳以上",
        },
    ]
    nlu = {"symptoms": [{"name": "頭痛"}]}
    filtered = _filter_medicines_when_age_unknown(
        meds, {}, nlu_result=nlu, user_text="頭痛い"
    )
    assert len(filtered) == 1
    assert filtered[0]["product_name"] == "小児用A"


def test_rule_based_headache_returns_analgesics(headache_flag_on):
    client = MagicMock()
    result = rule_based_medicine_recommendation("頭痛い", {}, client)
    meds = result.get("recommended_medicines") or []
    assert result.get("status") == "success"
    assert len(meds) >= 1
    assert any("解熱鎮痛薬" in str(m.get("medicine_type") or "") for m in meds)


def test_rule_based_dizziness_stays_empty(headache_flag_on):
    client = MagicMock()
    result = rule_based_medicine_recommendation(
        "めまいがする", {"age": 30}, client
    )
    assert is_caution_defer_single_symptom(result.get("nlu_result"))
    assert len(result.get("recommended_medicines") or []) == 0


def test_chat_filter_headache_pair(headache_flag_on):
    client = MagicMock()
    rb = rule_based_medicine_recommendation("頭痛い", {}, client)
    raw = rb.get("recommended_medicines") or []
    assert raw
    filtered = _filter_medicines_when_age_unknown(
        raw,
        {},
        nlu_result=rb.get("nlu_result"),
        user_text="頭痛い",
    )
    assert filtered

    dizzy = rule_based_medicine_recommendation("めまいがする", {}, client)
    dizzy_filtered = _filter_medicines_when_age_unknown(
        dizzy.get("recommended_medicines") or [],
        {},
        nlu_result=dizzy.get("nlu_result"),
        user_text="めまいがする",
    )
    assert dizzy_filtered == []
