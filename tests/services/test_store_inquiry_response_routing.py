"""店舗案内 fast-path の詳細分類・トイレ/商品区別の回帰テスト"""
from unittest.mock import MagicMock

import pytest

from src.services.concierge_intent import infer_structural_concierge_intent
from src.services.store_inquiry_handler import (
    _is_toilet_facility_request,
    _is_toilet_product_query,
    handle_store_inquiry_with_two_stage,
    is_probable_store_inquiry,
)


_TRIAGE_STORE = {
    "category": "Other",
    "subcategory": "store_inquiry",
    "confidence": 0.9,
}


@pytest.mark.parametrize(
    "text,expected_type,snippet",
    [
        ("映画館どこ？", "facilities", "映画館"),
        ("歯磨き粉どこ？", "inventory", "歯磨き粉"),
        (
            "トイレットペーパーはどこで売っていますか？",
            "inventory",
            "トイレットペーパー",
        ),
    ],
)
def test_fast_path_uses_detailed_classification(text, expected_type, snippet):
    result = handle_store_inquiry_with_two_stage(text, MagicMock(), dict(_TRIAGE_STORE))
    assert result is not None
    assert result["inquiry_type"] == expected_type
    assert snippet in result["response"]["simple_message"]


def test_toilet_need_routes_to_store_not_concierge_greeting():
    text = "うんこしたい"
    assert _is_toilet_facility_request(text) is True
    assert _is_toilet_product_query(text) is False
    assert is_probable_store_inquiry(text, _TRIAGE_STORE) is True
    physical_triage = {"category": "Physical", "subcategory": "constipation", "confidence": 0.9}
    assert is_probable_store_inquiry(text, physical_triage) is True
    assert infer_structural_concierge_intent(text) is None
    result = handle_store_inquiry_with_two_stage(text, MagicMock(), dict(_TRIAGE_STORE))
    assert result is not None
    assert "トイレ" in result["response"]["simple_message"]


def test_toilet_paper_is_product_not_facility():
    text = "トイレットペーパーはどこで売っていますか？"
    assert _is_toilet_product_query(text) is True
    assert _is_toilet_facility_request(text) is False
    result = handle_store_inquiry_with_two_stage(text, MagicMock(), dict(_TRIAGE_STORE))
    assert result["inquiry_type"] == "inventory"
    assert "トイレの場所" not in result["response"]["simple_message"]
