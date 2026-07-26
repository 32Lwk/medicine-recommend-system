"""medicine_qa_html — ストリーミング QA HTML。"""
from __future__ import annotations

from src.services.medicine_qa_html import build_chat_response_inner_html


def test_build_chat_response_inner_html_includes_product_images():
    html = build_chat_response_inner_html(
        {
            "answer": "ok",
            "product_images_html": '<div class="ui-qa-product-images">img</div>',
        }
    )
    assert "ui-qa-product-images" in html
    assert "qa-product-images" in html
