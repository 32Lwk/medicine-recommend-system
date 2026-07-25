"""medicine_image_urls — Cloudflare CDN URL 解決。"""
import os

import pytest

from src.services.medicine_image_urls import (
    build_medicine_image_cdn_url,
    enrich_medicine_image_url,
    load_otc_image_versions,
    record_otc_image_version,
    resolve_medicine_image_url,
    slugify_product_name,
)


@pytest.fixture(autouse=True)
def _cdn_base(monkeypatch):
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")


def test_explicit_https_preserved():
    med = {"product_name": "イブA錠", "image_url": "https://example.com/a.png"}
    assert resolve_medicine_image_url(med) == "https://example.com/a.png"


def test_cdn_from_product_name_encodes_japanese():
    med = {"product_name": "スカイブブロンのどスプレー", "manufacturer": "福地製薬"}
    url = resolve_medicine_image_url(med)
    assert url.startswith("https://images.yutok.dev/otc/%")
    assert ".webp" in url
    assert "?v=" in url


def test_cdn_from_product_name():
    med = {"product_name": "イブA錠", "manufacturer": "エスエス製薬"}
    url = resolve_medicine_image_url(med)
    assert url.startswith("https://images.yutok.dev/otc/")
    assert ".webp" in url


def test_image_slug_override():
    med = {"product_name": "x", "image_slug": "test"}
    assert resolve_medicine_image_url(med) == "https://images.yutok.dev/otc/test.webp"


def test_enrich_sets_image_url():
    row = enrich_medicine_image_url({"product_name": "カロナールA", "image_slug": "test"})
    assert row["image_url"] == "https://images.yutok.dev/otc/test.webp"
    assert row["product_image_url"] == row["image_url"]


def test_enrich_rewrites_stale_managed_cdn_url():
    stale = "https://images.yutok.dev/otc/スカイブブロンのどスプレー.webp"
    row = enrich_medicine_image_url(
        {"product_name": "スカイブブロンのどスプレー", "image_url": stale}
    )
    assert row["image_url"] != stale
    assert "%" in row["image_url"]
    assert "?v=" in row["image_url"]


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


def test_build_cdn_url_with_version():
    url = build_medicine_image_cdn_url(
        "https://images.yutok.dev/otc/",
        "スカイブブロンのどスプレー",
        version="abc12345",
    )
    assert "abc12345" in url
    assert "%E3%82%B9" in url


def test_record_and_load_image_version(tmp_path, monkeypatch):
    from src.services import medicine_image_urls as mod

    manifest = tmp_path / "versions.json"
    monkeypatch.setattr(mod, "_VERSIONS_PATH", manifest)
    mod.invalidate_otc_image_versions_cache()

    version = record_otc_image_version("テスト", b"image-bytes")
    assert version
    assert load_otc_image_versions()["テスト"] == version
