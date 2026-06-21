"""店舗周辺施設検出の文脈ゲートテスト"""
from src.agents.concierge_agent import should_concierge_handle
from src.services.store_inquiry_handler import (
    detect_facilities_inquiry,
    detect_store_inquiry_keywords,
    handle_store_inquiry_with_two_stage,
    is_probable_store_inquiry,
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


def test_toilet_where_without_ha_is_store_keyword():
    detected, itype = detect_store_inquiry_keywords("トイレどこ？")
    assert detected is True
    assert itype == "store_inquiry"


def test_toilet_where_is_probable_store_inquiry():
    assert is_probable_store_inquiry("トイレどこ？", {"category": "Other"}) is True


def test_concierge_skips_probable_store_inquiry():
    assert should_concierge_handle("トイレどこ？", {"category": "Other", "confidence": 0.8}) is False


def test_defer_when_concierge_intent_on_triage_but_store_wins():
    assert should_defer_store_to_concierge(
        "トイレどこ？",
        {"concierge_intent": "redirect", "category": "Other"},
    ) is False


def test_defer_when_concierge_intent_on_ambiguous_facility():
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


def test_handle_store_toilet_fast_path_without_client():
    result = handle_store_inquiry_with_two_stage(
        "トイレどこ？",
        None,  # type: ignore[arg-type]
        {"category": "Other", "confidence": 0.7, "subcategory": "general_other"},
    )
    assert result is not None
    assert result["is_store_inquiry"] is True
    assert "トイレ" in result["response"]["simple_message"]


def test_handle_store_after_basic_normalize():
    """chat_post_pipeline の preprocess 後（といれどこ?）でも fast-path する。"""
    from src.handlers.chat.chat_preprocess_route import preprocess_user_message

    class _S:
        pass

    _, processed = preprocess_user_message(_S(), None, "トイレどこ？")
    result = handle_store_inquiry_with_two_stage(
        processed,
        None,  # type: ignore[arg-type]
        {"category": "Other", "confidence": 0.7, "subcategory": "general_other"},
    )
    assert result is not None
    assert result["is_store_inquiry"] is True
