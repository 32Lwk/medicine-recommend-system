"""Tests for recommendation diagnosis v1 schema."""
from src.schemas.recommendation_diagnosis_v1 import (
    DiagnosisV1,
    RecoError,
    UsageSection,
    strip_for_user_api,
)


def test_diagnosis_v1_minimal():
    d = DiagnosisV1(render="sage_reco", symptoms=["頭痛"])
    data = d.to_client_dict()
    assert data["schema_version"] == 1
    assert data["render"] == "sage_reco"
    assert data["symptoms"] == ["頭痛"]


def test_strip_for_user_api_removes_admin():
    d = DiagnosisV1(
        render="sage_reco",
        admin={"score_breakdown": {"x": 1}},
        recommended_medicines=[{"product_name": "A", "score": 0.9}],
    )
    user = strip_for_user_api(d.to_client_dict())
    assert "admin" not in user


def test_reco_error_severity():
    err = RecoError(
        type="no_candidates",
        severity="warn",
        title="t",
        message="m",
    )
    assert err.type == "no_candidates"
