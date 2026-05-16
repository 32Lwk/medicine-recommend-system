"""店舗周辺施設検出の文脈ゲートテスト"""
from src.services.store_inquiry_handler import (
    detect_facilities_inquiry,
    detect_store_inquiry_keywords,
    handle_store_inquiry_with_two_stage,
    should_defer_store_to_concierge,
)


def test_university_where_deferred_not_facilities():
    assert should_defer_store_to_concierge("大学はどこ？") is True
    ok, name = detect_facilities_inquiry("大学はどこ？")
    assert ok is False
    assert name is None


def test_nearby_university_is_facilities():
    ok, name = detect_facilities_inquiry("近くの大学はどこ？")
    assert ok is True
    assert name == "大学"


def test_convenience_with_location_question():
    ok, name = detect_facilities_inquiry("コンビニはどこ？")
    assert ok is True


def test_bare_doko_not_store_keyword():
    detected, _ = detect_store_inquiry_keywords("大学はどこ？")
    assert detected is False


def test_toilet_where_is_store_keyword():
    detected, itype = detect_store_inquiry_keywords("トイレはどこ？")
    assert detected is True
    assert itype == "store_inquiry"


def test_defer_when_concierge_intent_on_triage():
    assert should_defer_store_to_concierge(
        "場所を教えて",
        {"concierge_intent": "doc_operator"},
    ) is True


def test_handle_store_skips_university_without_client():
    result = handle_store_inquiry_with_two_stage(
        "大学はどこ？",
        None,  # type: ignore[arg-type]
        {"category": "Other", "confidence": 0.84, "subcategory": "store_inquiry"},
    )
    assert result is None
