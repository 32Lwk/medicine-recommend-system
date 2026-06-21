"""在庫照会の商品スキャン短絡・店舗ゲートキャッシュ・商品インデックス"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.routing_context import RoutingContext, evaluate_store_gate
from src.services.store_inquiry_handler import detect_inventory_inquiry
from src.services.store_product_index import classify_product_category, index_stats


_TRIAGE_OTHER = {"category": "Other", "confidence": 0.9, "subcategory": "general_other"}


@pytest.mark.parametrize(
    "text",
    [
        "おはよ",
        "konn",
        "こんにちは",
        "今日はいい天気",
    ],
)
def test_inventory_scan_skipped_for_non_inventory_inputs(text: str):
    with patch(
        "src.services.store_inquiry_handler.classify_product_category"
    ) as mock_classify:
        ok, info = detect_inventory_inquiry(text, _TRIAGE_OTHER)
        assert ok is False
        assert info is None
        mock_classify.assert_not_called()


def test_inventory_scan_runs_for_product_location_question():
    with patch(
        "src.services.store_inquiry_handler.classify_product_category",
        return_value={
            "category": "ビューティ・トイレタリー",
            "subcategory": "歯ブラシ",
            "product": "歯ブラシ",
            "matched_keyword": "歯ブラシ",
        },
    ) as mock_classify:
        ok, info = detect_inventory_inquiry("歯ブラシどこ？", _TRIAGE_OTHER)
        assert ok is True
        assert info is not None
        assert info["product"] == "歯ブラシ"
        mock_classify.assert_called_once()


def test_product_index_finds_toothbrush():
    stats = index_stats()
    assert stats["unique_tokens"] > 0
    found = classify_product_category("歯ブラシはどこ？")
    assert found is not None
    assert "歯ブラシ" in (found.get("product") or found.get("matched_keyword") or "")


def test_store_gate_cache_avoids_double_evaluation():
    routing = RoutingContext(
        session_id="s1",
        user_text="トイレどこ？",
        sanitized_text="トイレどこ？",
        triage_result=_TRIAGE_OTHER,
    )
    with patch(
        "src.services.store_inquiry_handler.is_probable_store_inquiry_any",
        return_value=True,
    ) as mock_probable:
        first = evaluate_store_gate(
            "トイレどこ？",
            triage_result=_TRIAGE_OTHER,
            routing_ctx=routing,
        )
        second = evaluate_store_gate(
            "トイレどこ？",
            triage_result=_TRIAGE_OTHER,
            routing_ctx=routing,
        )
        assert first is True
        assert second is True
        assert routing.store_gate_evaluated is True
        mock_probable.assert_called_once()


def test_store_gate_cache_respects_medical_priority():
    routing = RoutingContext(
        session_id="s1",
        user_text="風邪薬ありますか",
        sanitized_text="風邪薬ありますか",
        triage_result={"category": "Physical", "confidence": 0.95},
    )
    with patch(
        "src.services.store_inquiry_handler.is_probable_store_inquiry_any",
        return_value=True,
    ) as mock_probable:
        with patch(
            "src.utils.input_helpers.should_prioritize_medical_route_over_store",
            return_value=True,
        ):
            result = evaluate_store_gate(
                "風邪薬ありますか",
                triage_result=routing.triage_result,
                routing_ctx=routing,
            )
        assert result is False
        mock_probable.assert_not_called()
