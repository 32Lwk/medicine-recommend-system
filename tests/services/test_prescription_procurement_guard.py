"""医薬品購入先の店舗/薬局案内ルーティング（jsonl_10 回帰）"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.concierge_intent import infer_structural_concierge_intent
from src.services.concierge_orchestrator import enrich_other_concierge_intent
from src.services.counseling_triage import (
    classify_medicine_procurement_route,
    detect_inappropriate_request,
    detect_prescription_procurement_request,
    is_treatment_mention,
)
from src.services.meta_triage import should_skip_meta_triage_llm
from src.services.store_inquiry_handler import (
    is_probable_store_inquiry,
    process_detailed_classification,
)

_TRIAGE_GENERAL = {
    "category": "Other",
    "confidence": 0.93,
    "subcategory": "general_other",
}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("処方箋なしの購入先", "otc_store"),
        ("処方箋なしで買いたい", "otc_store"),
        ("RXなしの購入先", "otc_store"),
        ("prescription の where to buy", "pharmacy_prescription"),
        ("処方箋の購入先", "pharmacy_prescription"),
    ],
)
def test_classify_medicine_procurement_route(text: str, expected: str):
    assert classify_medicine_procurement_route(text) == expected
    assert detect_prescription_procurement_request(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "こんにちは",
        "頭が痛い",
        "トイレどこ",
        "向精神薬の購入先",
    ],
)
def test_classify_medicine_procurement_negative(text: str):
    assert classify_medicine_procurement_route(text) is None
    assert detect_prescription_procurement_request(text) is False


def test_procurement_not_inappropriate_block_from_general_other():
    triage = dict(_TRIAGE_GENERAL)
    assert detect_inappropriate_request("処方箋なしの購入先", triage) is None


def test_procurement_routes_to_store_inquiry():
    assert is_probable_store_inquiry("処方箋なしの購入先", _TRIAGE_GENERAL) is True


def test_procurement_detailed_classification():
    result = process_detailed_classification(
        "処方箋なしの購入先",
        {"inquiry_type": "store_inquiry", "confidence": 0.9},
        _TRIAGE_GENERAL,
    )
    assert result is not None
    assert result["is_store_inquiry"] is True
    assert result.get("procurement_route") == "otc_store"


def test_prescription_procurement_routes_to_pharmacy():
    result = process_detailed_classification(
        "処方箋の購入先",
        {"inquiry_type": "store_inquiry", "confidence": 0.9},
        _TRIAGE_GENERAL,
    )
    assert result is not None
    assert result.get("procurement_route") == "pharmacy_prescription"
    assert result.get("facility_name") == "薬局"


def test_treatment_mention_does_not_match_no_prescription_phrase():
    assert is_treatment_mention("処方箋なしの購入先") is False


def test_structural_greeting_rejects_prescription_procurement():
    assert infer_structural_concierge_intent("処方箋なしの購入先") is None


def test_should_not_skip_meta_for_prescription_procurement():
    assert (
        should_skip_meta_triage_llm(
            _TRIAGE_GENERAL,
            "処方箋なしの購入先",
            store_probable=True,
        )
        is False
    )


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_does_not_structural_greeting_for_procurement(mock_meta):
    mock_meta.return_value = "redirect"
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE_GENERAL),
        "処方箋なしの購入先",
        MagicMock(),
    )
    assert enriched.get("concierge_intent") != "greeting"
    assert enriched.get("concierge_intent_source") != "structural_greeting"


def test_security_validator_compiles_and_validates_procurement_text():
    from src.security.security_validator import validate_user_input

    is_safe, score, warnings, _ = validate_user_input("処方箋なしの購入先", context="chat")
    assert isinstance(is_safe, bool)
    assert isinstance(score, int)
