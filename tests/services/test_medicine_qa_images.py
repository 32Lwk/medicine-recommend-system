"""medicine_qa_images テスト。"""
from __future__ import annotations

from src.services.medicine_qa_images import (
    NOIMAGE_HERO_PATH,
    NOIMAGE_LABEL,
    build_product_image_answer_text,
    build_product_images_html,
)


def test_build_product_image_answer_text_not_ready_with_summary():
    text = build_product_image_answer_text(
        [{"product_name": "カロナールA", "ingredients": "アセトアミノフェン"}]
    )
    assert "まだ準備できていません" in text
    assert "アセトアミノフェン" in text
    assert "頭痛" in text
    assert "見せられ" not in text


def test_build_product_image_answer_text_two_products():
    text = build_product_image_answer_text(
        [
            {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェン"},
            {"product_name": "イブ", "ingredients": "イブプロフェン"},
        ]
    )
    assert "まだ準備できていません" in text
    assert "ロキソニンＳ" in text
    assert "イブ" in text
    assert "主成分" in text


def test_build_product_image_answer_text_ready_when_manifest_has_slug(monkeypatch, tmp_path):
    from src.services import medicine_image_urls as mod

    manifest = tmp_path / "versions.json"
    manifest.write_text('{"カロナールA": "abc12345"}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_VERSIONS_PATH", manifest)
    mod.invalidate_otc_image_versions_cache()
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")

    text = build_product_image_answer_text(
        [{"product_name": "カロナールA", "ingredients": "アセトアミノフェン"}]
    )
    assert "パッケージ画像です。" in text
    assert "まだ準備できていません" not in text
    assert "アセトアミノフェン" in text


def test_build_product_image_answer_text_partial_ready_names_products(monkeypatch, tmp_path):
    from src.services import medicine_image_urls as mod

    manifest = tmp_path / "versions.json"
    manifest.write_text('{"ロキソニンS": "abc12345"}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_VERSIONS_PATH", manifest)
    mod.invalidate_otc_image_versions_cache()
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")

    text = build_product_image_answer_text(
        [
            {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェン"},
            {"product_name": "イブ", "ingredients": "イブプロフェン"},
        ]
    )
    assert "ロキソニンＳのパッケージ画像を表示しました。" in text
    assert "イブのパッケージ画像はまだ準備できていません。" in text
    assert "一部は" not in text
    assert "主成分" in text


def test_build_product_images_html_renders_noimage_placeholder_without_url(monkeypatch):
    monkeypatch.delenv("MEDICINE_IMAGE_CDN_BASE", raising=False)
    html = build_product_images_html([{"product_name": "存在しないテスト用製品XYZ"}])
    assert "ui-qa-product-images" in html
    assert "存在しないテスト用製品XYZ" in html
    assert "ui-qa-product-images__item" in html
    assert "ui-med-image--placeholder" in html
    assert NOIMAGE_LABEL in html
    assert "ui-qa-product-images__ph" not in html


def test_build_product_images_html_uses_reco_style_with_onerror(monkeypatch):
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")
    html = build_product_images_html([{"product_name": "イブ", "manufacturer": "エスエス製薬"}])
    assert "ui-med-image--card" in html
    assert NOIMAGE_HERO_PATH in html
    assert "onerror=" in html
    assert "ui-qa-product-images--count-1" in html


def test_build_product_images_html_two_column_class(monkeypatch):
    monkeypatch.delenv("MEDICINE_IMAGE_CDN_BASE", raising=False)
    html = build_product_images_html(
        [
            {"product_name": "ロキソニンＳ"},
            {"product_name": "イブ"},
        ]
    )
    assert "ui-qa-product-images--count-2" in html
    assert html.count("ui-med-image--card") == 2
