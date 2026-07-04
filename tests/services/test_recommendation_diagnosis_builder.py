"""Tests for recommendation_diagnosis_builder."""
from src.services.recommendation_diagnosis_builder import (
    SAGE_RECO_MARKER,
    build_diagnosis_v1,
    build_display_summary,
    build_reco_error,
    build_usage_sections,
)


def test_build_diagnosis_success():
    result = {
        "status": "success",
        "symptoms": ["頭痛"],
        "medicine_type": "解熱鎮痛薬",
        "recommended_medicines": [
            {
                "rank": 1,
                "product_name": "テスト薬",
                "manufacturer": "メーカー",
                "explanation": "理由",
                "score": 0.85,
            }
        ],
        "usage_notes": "1つ目：テスト薬\n・用法",
        "doctor_consultation": "改善しない場合は受診",
        "personalized_advice": "水分補給を",
        "algorithm": "rule_based",
    }
    diag = build_diagnosis_v1(result, session_id="sess-1")
    assert diag.render == "sage_reco"
    assert len(diag.recommended_medicines) == 1
    assert diag.personalized_advice == "水分補給を"
    assert diag.admin and diag.admin.get("session_id") == "sess-1"


def test_build_diagnosis_no_candidates():
    result = {
        "status": "success",
        "symptoms": ["腹痛"],
        "recommended_medicines": [],
    }
    diag = build_diagnosis_v1(result)
    assert diag.error is not None
    assert diag.error.type == "no_candidates"
    assert diag.error.severity == "warn"


def test_build_usage_sections_text():
    sections = build_usage_sections("【使ってはいけない人】\n・妊娠中")
    assert len(sections) == 1
    assert sections[0].kind == "contraindication"
    assert "妊娠中" in sections[0].items[0]


def test_build_display_summary():
    diag = build_diagnosis_v1(
        {
            "symptoms": ["咳"],
            "recommended_medicines": [{"product_name": "薬A"}],
        }
    )
    summary = build_display_summary(diag)
    assert "咳" in summary
    assert "薬A" in summary


def test_build_diagnosis_age_policy_notice():
    result = {
        "symptoms": ["発熱"],
        "recommended_medicines": [{"product_name": "テスト薬", "age_restriction": "15歳以上"}],
        "age_policy_notice": "年齢未確認の注意",
    }
    diag = build_diagnosis_v1(result)
    assert diag.age_policy_notice == "年齢未確認の注意"


def test_build_diagnosis_age_policy_fallback_when_v2(monkeypatch):
    monkeypatch.setenv("RECO_AGE_POLICY_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    result = {
        "symptoms": ["発熱"],
        "recommended_medicines": [
            {"product_name": "カロナールA", "age_restriction": "15歳以上"},
        ],
        "user_info": {"age": None},
    }
    diag = build_diagnosis_v1(result)
    assert "年齢" in diag.age_policy_notice
    assert "カロナールA" in diag.age_policy_notice
    assert diag.admin and diag.admin.get("restricted_medicines") == ["カロナールA"]


def test_sage_reco_marker_constant():
    assert SAGE_RECO_MARKER == "sage_reco"


def test_build_reco_error_mapping():
    err = build_reco_error("missing_critical_info", {"reason": "症状なし"})
    assert err.type == "missing_info"
    assert err.severity == "warn"
