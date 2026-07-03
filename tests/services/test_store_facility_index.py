"""施設インデックスと商品インデックスの分離テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.store_facility_index import (
    find_facility_in_text,
    index_stats,
    is_facility_name,
    is_store_locator_query,
    reset_facility_index_cache,
)
from src.services.store_inquiry_handler import (
    detect_inventory_inquiry,
    handle_store_inquiry_with_two_stage,
)
from src.services.store_product_index import (
    classify_product_category,
    reset_product_index_cache,
)


_TRIAGE_STORE = {
    "category": "Other",
    "subcategory": "store_inquiry",
    "confidence": 0.9,
}


@pytest.fixture(autouse=True)
def _reset_caches():
    reset_facility_index_cache()
    reset_product_index_cache()
    yield
    reset_facility_index_cache()
    reset_product_index_cache()


def test_facility_index_includes_drugstore_and_chains():
    stats = index_stats()
    assert stats["total_tokens"] > 50
    assert is_facility_name("ドラッグストア")
    assert is_facility_name("マツキヨ")
    assert is_facility_name("セブンイレブン")


def test_product_index_does_not_match_drugstore_location_query():
    found = classify_product_category("ドラッグストアはどこ？")
    assert found is None


def test_product_index_still_finds_real_products():
    found = classify_product_category("歯ブラシはどこ？")
    assert found is not None
    assert "歯ブラシ" in (found.get("product") or found.get("matched_keyword") or "")


def test_matsukiyo_cosme_brand_not_facility_name():
    """商品ブランド「マツキヨコスメ」は施設名と区別する。"""
    assert not is_facility_name("マツキヨコスメ")
    found = classify_product_category("マツキヨコスメはありますか")
    assert found is not None


@pytest.mark.parametrize(
    "text",
    [
        "ドラッグストアはどこ？",
        "マツキヨは近くにありますか",
    ],
)
def test_store_locator_not_inventory(text: str):
    assert is_store_locator_query(text)
    ok, info = detect_inventory_inquiry(text, _TRIAGE_STORE)
    assert ok is False
    assert info is None


def test_drugstore_where_returns_store_guidance_not_inventory():
    result = handle_store_inquiry_with_two_stage(
        "ドラッグストアはどこ？",
        MagicMock(),
        dict(_TRIAGE_STORE),
    )
    assert result is not None
    assert result["inquiry_type"] == "store_inquiry"
    msg = result["response"]["simple_message"]
    assert "当キオスク" not in msg
    assert "在庫" not in msg
    assert "店内" in msg
    assert "お店の外" in msg or "近く" in msg


def test_facilities_response_covers_inside_and_outside():
    from src.services.store_inquiry_handler import generate_facilities_inquiry_response

    msg = generate_facilities_inquiry_response("映画館どこ？", "映画館")["simple_message"]
    assert "当キオスク" not in msg
    assert "店内" in msg
    assert "お店の外" in msg
    assert "地図" in msg


def test_find_facility_prefers_longest_match():
    assert find_facility_in_text("マツキヨは近く") == "マツキヨ"
    assert find_facility_in_text("ドラッグストアはどこ") == "ドラッグストア"
