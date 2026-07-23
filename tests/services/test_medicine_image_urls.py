"""medicine_image_urls — Cloudflare CDN URL 解決。"""
import os

import pytest

from src.services.medicine_image_urls import (
    enrich_medicine_image_url,
    resolve_medicine_image_url,
    slugify_product_name,
)


@pytest.fixture(autouse=True)
def _cdn_base(monkeypatch):
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")


def test_explicit_https_preserved():
    med = {"product_name": "イブA錠", "image_url": "https://example.com/a.png"}
    assert resolve_medicine_image_url(med) == "https://example.com/a.png"


def test_cdn_from_product_name():
    med = {"product_name": "イブA錠", "manufacturer": "エスエス製薬"}
    url = resolve_medicine_image_url(med)
    assert url.startswith("https://images.yutok.dev/otc/")
    assert url.endswith(".webp")


def test_image_slug_override():
    med = {"product_name": "x", "image_slug": "test"}
    assert resolve_medicine_image_url(med) == "https://images.yutok.dev/otc/test.webp"


def test_enrich_sets_image_url():
    row = enrich_medicine_image_url({"product_name": "カロナールA", "image_slug": "test"})
    assert row["image_url"] == "https://images.yutok.dev/otc/test.webp"
    assert row["product_image_url"] == row["image_url"]


def test_no_cdn_when_env_unset(monkeypatch):
    monkeypatch.delenv("MEDICINE_IMAGE_CDN_BASE", raising=False)
    assert resolve_medicine_image_url({"product_name": "イブ"}) is None


def test_slugify_fallback_hash():
    slug = slugify_product_name("!!!", "")
    assert slug.startswith("p-")


def test_flex_resolve_uses_cdn(monkeypatch):
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")
    from src.handlers.line.flex_messages import resolve_medicine_hero_url

    url = resolve_medicine_hero_url({"product_name": "テスト", "image_slug": "test"})
    assert url == "https://images.yutok.dev/otc/test.webp"
