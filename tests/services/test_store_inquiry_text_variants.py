"""正規化後テキストと原文の両方で店舗案内が通ること"""
from src.handlers.chat.chat_preprocess_route import preprocess_user_message
from src.services.concierge_templates import build_redirect_text
from src.services.store_inquiry_handler import (
    handle_store_inquiry_with_two_stage,
    is_probable_store_inquiry,
)


class _Session:
    pass


_TRIAGE = {"category": "Other", "confidence": 0.8, "subcategory": "general_other"}


def test_sanitized_toothbrush_inventory_after_normalize():
    raw = "歯ブラシはどこ？"
    sanitized, _ = preprocess_user_message(_Session(), None, raw)
    assert sanitized != raw
    assert is_probable_store_inquiry(sanitized, _TRIAGE) is True
    result = handle_store_inquiry_with_two_stage(
        sanitized,
        None,
        _TRIAGE,
        extra_texts=[raw],
    )
    assert result is not None
    assert result["response"]["simple_message"] != build_redirect_text()
    assert "スタッフ" in result["response"]["simple_message"]


def test_sanitized_convenience_facilities_after_normalize():
    raw = "コンビニはどこ？"
    sanitized, _ = preprocess_user_message(_Session(), None, raw)
    assert is_probable_store_inquiry(sanitized, _TRIAGE) is True
    result = handle_store_inquiry_with_two_stage(sanitized, None, _TRIAGE)
    assert result is not None
    assert "スタッフ" in result["response"]["simple_message"]


def test_sanitized_toilet_not_redirect_text():
    raw = "トイレどこ？"
    sanitized, _ = preprocess_user_message(_Session(), None, raw)
    result = handle_store_inquiry_with_two_stage(sanitized, None, _TRIAGE)
    assert result is not None
    assert result["response"]["simple_message"] != build_redirect_text()
