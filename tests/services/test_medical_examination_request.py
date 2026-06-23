"""医療行為依頼の検出・境界応答"""
from unittest.mock import MagicMock, patch

from src.services.counseling.counseling_generator import generate_counseling_response
from src.services.counseling.counseling_templates import MEDICAL_EXAMINATION_BOUNDARY
from src.services.counseling_triage import detect_inappropriate_request
from src.services.llm_triage import llm_triage
from src.services.medical_examination_request import (
    MEDICAL_EXAMINATION_EXACT_PHRASES,
    detect_medical_examination_request_exact,
    resolve_medical_examination_request_type,
)


def test_exact_phrase_matches_examination_request():
    assert detect_medical_examination_request_exact("診察してください")
    assert detect_medical_examination_request_exact("診察してください。")


def test_exact_phrase_does_not_match_compound_sentence():
    assert not detect_medical_examination_request_exact("39度の熱があるので診察してください")
    assert not detect_medical_examination_request_exact("腹が痛いので診察してください")
    assert not detect_medical_examination_request_exact("診断された")


def test_all_catalog_phrases_are_exact_only():
    for phrase in MEDICAL_EXAMINATION_EXACT_PHRASES:
        assert detect_medical_examination_request_exact(phrase)
        assert not detect_medical_examination_request_exact(f"頭痛で{phrase}")


def test_resolve_from_llm_flag():
    triage = {
        "category": "Other",
        "medical_examination_request": True,
        "subcategory": "inappropriate_request/medical_examination",
    }
    assert resolve_medical_examination_request_type("腹が痛いので診察してください", triage) == (
        "medical_examination"
    )


def test_llm_triage_exact_fast_path():
    result = llm_triage("診察してください", MagicMock(), use_cache=False)
    assert result["subcategory"] == "inappropriate_request/medical_examination"
    assert result["category"] == "Other"


def test_llm_triage_stage1_medical_examination_flag():
    stage1 = {
        "category": "Physical",
        "confidence": 0.98,
        "subcategory": "abdominal_pain",
        "medical_examination_request": True,
        "requires_immediate_action": False,
        "reasoning": "診察依頼を検出",
    }

    with patch("src.core.llm_client.chat_completion_create") as mock_llm:
        mock_llm.return_value.choices[0].message.content = __import__("json").dumps(stage1)
        result = llm_triage("腹が痛いので診察してください", MagicMock(), use_cache=False)

    assert result["category"] == "Other"
    assert result["subcategory"] == "inappropriate_request/medical_examination"
    assert result.get("medical_examination_request") is True
    mock_llm.assert_called_once()


def test_detect_inappropriate_from_triage_subcategory():
    triage = {
        "category": "Other",
        "subcategory": "inappropriate_request/medical_examination",
        "confidence": 0.95,
    }
    assert detect_inappropriate_request("医者に見てほしい", triage) == "medical_examination"


def test_counseling_response_uses_static_boundary():
    text = generate_counseling_response(
        "inappropriate_request/medical_examination",
        "診察してください",
        None,
    )
    assert text == MEDICAL_EXAMINATION_BOUNDARY
    assert "承知" not in text
