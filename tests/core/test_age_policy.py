"""Tests for age_policy (RECO_AGE_POLICY_V2)."""
from __future__ import annotations

from src.core.recommendation.age_policy import (
    AGE_UNKNOWN_NOTICE_HEADER,
    apply_age_unknown_policy_to_result,
    build_age_unknown_notice,
    medicines_with_age_restriction_gte,
    parse_min_age_years,
    prepend_age_notice_to_usage_notes,
)


def test_parse_min_age_years():
    assert parse_min_age_years("15歳以上") == 15
    assert parse_min_age_years("12歳未満禁止") == 12
    assert parse_min_age_years("") is None


def test_medicines_with_age_restriction_gte():
    meds = [
        {"product_name": "A", "age_restriction": "15歳以上"},
        {"product_name": "B", "age_restriction": "7歳以上"},
        {"product_name": "C", "age_restriction": ""},
    ]
    restricted = medicines_with_age_restriction_gte(meds, min_years=12)
    assert len(restricted) == 1
    assert restricted[0]["product_name"] == "A"


def test_build_age_unknown_warnings():
    from src.core.recommendation.age_policy import build_age_unknown_warnings

    warnings = build_age_unknown_warnings(
        [{"product_name": "カロナールA", "age_restriction": "15歳以上"}],
        {"age": None},
    )
    assert warnings
    assert "カロナールA" in warnings["age_policy_notice"]
    assert warnings["restricted_medicines"] == ["カロナールA"]
    assert build_age_unknown_warnings([], {"age": None}) is None
    assert build_age_unknown_warnings(
        [{"product_name": "A", "age_restriction": "15歳以上"}],
        {"age": 20},
    ) is None


def test_build_age_unknown_notice():
    notice = build_age_unknown_notice(
        [{"product_name": "カロナールA", "age_restriction": "15歳以上"}]
    )
    assert notice
    assert "カロナールA" in notice


def test_prepend_age_notice_to_usage_notes():
    out = prepend_age_notice_to_usage_notes("用法メモ", "テスト注意")
    assert AGE_UNKNOWN_NOTICE_HEADER in out
    assert "用法メモ" in out


def test_apply_age_unknown_policy_v2(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    result = {
        "recommended_medicines": [
            {"product_name": "イブ", "age_restriction": "15歳以上"},
        ],
        "usage_notes": "添付文書をよく読んでご使用ください。",
    }
    apply_age_unknown_policy_to_result(result, {"age": None})
    assert result.get("age_policy_notice")
    assert result.get("restricted_medicines") == ["イブ"]
    assert AGE_UNKNOWN_NOTICE_HEADER in result["usage_notes"]


def test_apply_age_unknown_policy_skips_when_age_known(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    result = {
        "recommended_medicines": [
            {"product_name": "イブ", "age_restriction": "15歳以上"},
        ],
        "usage_notes": "用法",
    }
    apply_age_unknown_policy_to_result(result, {"age": 30})
    assert "age_policy_notice" not in result
