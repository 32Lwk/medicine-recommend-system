"""小児発熱の安全ガード（年齢未入力）。"""
from __future__ import annotations

from src.handlers.chat.chat_recommendation_flow import (
    _filter_medicines_when_age_unknown,
    _pediatric_context_without_confirmed_age,
)


def test_pediatric_context_detected_without_age() -> None:
    assert _pediatric_context_without_confirmed_age("子どもが熱を出しました", {}) is True
    assert _pediatric_context_without_confirmed_age("頭痛です", {}) is False
    assert _pediatric_context_without_confirmed_age("子どもが熱", {"age": 5}) is False


def test_filter_age_restricted_medicines_when_age_unknown() -> None:
    meds = [
        {"product_name": "A", "age_restriction": "15歳以上"},
        {"product_name": "B", "age_restriction": "7歳以上"},
    ]
    filtered = _filter_medicines_when_age_unknown(meds, {})
    assert len(filtered) == 1
    assert filtered[0]["product_name"] == "B"


def test_no_filter_when_age_known() -> None:
    meds = [{"product_name": "A", "age_restriction": "15歳以上"}]
    assert _filter_medicines_when_age_unknown(meds, {"age": 20}) == meds
