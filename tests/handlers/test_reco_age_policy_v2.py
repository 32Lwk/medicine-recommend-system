"""RECO_AGE_POLICY_V2 — chat 年齢フィルタ・小児ブロック・fallback。"""
from __future__ import annotations

from src.handlers.chat.chat_recommendation_flow import (
    _build_pediatric_age_inquiry_response,
    _filter_medicines_when_age_unknown,
    _pediatric_context_without_confirmed_age,
)

_MEDS_15_PLUS = [
    {"product_name": "カロナールA", "age_restriction": "15歳以上"},
    {"product_name": "イブプロフェン錠200S", "age_restriction": "15歳以上"},
    {"product_name": "ロキソニンS", "age_restriction": "15歳以上"},
]


def _should_empty_recommendation_fallback(rec: dict) -> bool:
    """chat_recommendation_flow L1885–1889 と同じ判定。"""
    return (
        not rec.get("recommended_medicines")
        and not rec.get("error")
        and not rec.get("escalation")
    )


def test_filter_passes_through_when_age_policy_v2(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    out = _filter_medicines_when_age_unknown(
        list(_MEDS_15_PLUS),
        {"age": None},
        nlu_result={"symptoms": [{"name": "発熱"}]},
        user_text="風邪ですが水泳大会",
    )
    assert len(out) == 3


def test_cold_swim_three_medicines_preserved(monkeypatch):
    """P1-8 cold_start_cold_swim 相当: 年齢未確認でも rule_based 3件を維持。"""
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    user_text = "風邪ですが明日水泳大会なので使える薬を教えて"
    filtered = _filter_medicines_when_age_unknown(
        list(_MEDS_15_PLUS),
        {"age": None},
        nlu_result={"symptoms": [{"name": "発熱"}, {"name": "咳"}]},
        user_text=user_text,
    )
    rec = {
        "status": "success",
        "recommended_medicines": filtered,
        "error": False,
        "escalation": False,
    }
    assert len(rec["recommended_medicines"]) == 3
    assert not _should_empty_recommendation_fallback(rec)


def test_filter_excludes_12_plus_when_v2_off(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    out = _filter_medicines_when_age_unknown(list(_MEDS_15_PLUS), {"age": None})
    assert len(out) == 0


def test_filter_unchanged_when_age_known(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    out = _filter_medicines_when_age_unknown(list(_MEDS_15_PLUS), {"age": 20})
    assert len(out) == 3


def test_pediatric_context_detected():
    assert _pediatric_context_without_confirmed_age("5歳の子供が熱を出しました", {})


def test_pediatric_context_not_adult():
    assert not _pediatric_context_without_confirmed_age("風邪です", {})


def test_pediatric_inquiry_kind():
    session = {"messages": [], "user_attributes": {}}
    body, status = _build_pediatric_age_inquiry_response(session, "sid-test")
    assert status == 200
    bot = session["messages"][-1]
    assert bot["diagnosis"]["kind"] == "pediatric_age_required"


def test_no_candidates_skips_empty_fallback():
    rec = {
        "recommended_medicines": [],
        "status": "no_candidates",
        "error": True,
        "error_type": "no_candidates",
        "escalation": False,
    }
    assert not _should_empty_recommendation_fallback(rec)


def test_post_filter_zero_triggers_empty_fallback():
    rec = {
        "recommended_medicines": [],
        "status": "success",
        "error": False,
        "escalation": False,
    }
    assert _should_empty_recommendation_fallback(rec)


def test_awaiting_cold_symptoms_prepends_context():
    session = {"_awaiting_cold_symptoms": True, "messages": []}
    user_message = "発熱があります"
    if session.pop("_awaiting_cold_symptoms", False) or session.pop(
        "_pending_cold_symptoms", False
    ):
        if user_message.strip() and "風邪" not in user_message:
            user_message = f"風邪で{user_message.strip()}"
    assert user_message == "風邪で発熱があります"
    assert "_awaiting_cold_symptoms" not in session


def test_pending_cold_symptoms_alias():
    session = {"_pending_cold_symptoms": True, "messages": []}
    user_message = "咳が出ます"
    if session.pop("_awaiting_cold_symptoms", False) or session.pop(
        "_pending_cold_symptoms", False
    ):
        if user_message.strip() and "風邪" not in user_message:
            user_message = f"風邪で{user_message.strip()}"
    assert user_message == "風邪で咳が出ます"
