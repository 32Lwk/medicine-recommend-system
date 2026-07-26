"""medicine_qa_images テスト。"""
from __future__ import annotations

from src.services.medicine_qa_images import build_product_images_html


def test_build_product_images_html_renders_figure():
    html = build_product_images_html([{"product_name": "存在しないテスト用製品XYZ"}])
    assert "ui-qa-product-images" in html
    assert "存在しないテスト用製品XYZ" in html
    assert "ui-qa-product-images__item" in html
