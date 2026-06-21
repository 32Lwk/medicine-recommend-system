"""Tests for GET /api/sessions diagnosis sanitization."""
from src.schemas.recommendation_diagnosis_v1 import strip_for_user_api


def test_strip_removes_admin_from_message_diagnosis():
    msg = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": {
            "render": "sage_reco",
            "admin": {"score_breakdown": {"x": 1}},
            "recommended_medicines": [{"product_name": "A", "score": 0.9}],
        },
    }
    msg["diagnosis"] = strip_for_user_api(msg["diagnosis"])
    assert "admin" not in msg["diagnosis"]
