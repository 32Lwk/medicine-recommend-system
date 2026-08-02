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


@pytest.fixture(autouse=True)
def _reset_otc_image_versions_cache():
    from src.services.medicine_image_urls import invalidate_otc_image_versions_cache

    invalidate_otc_image_versions_cache()
    yield
    invalidate_otc_image_versions_cache()


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


def test_cloud_run_fallback_cdn_base(monkeypatch):
    from config.aws_features import get_medicine_image_cdn_base

    monkeypatch.delenv("MEDICINE_IMAGE_CDN_BASE", raising=False)
    monkeypatch.setenv("K_SERVICE", "medicine-recommend")
    assert get_medicine_image_cdn_base() == "https://images.yutok.dev/otc/"


def test_image_slug_override():
    med = {"product_name": "x", "image_slug": "test"}
    assert resolve_medicine_image_url(med) == "https://images.yutok.dev/otc/test.webp"


def test_medicine_has_ready_image_uses_manifest(monkeypatch, tmp_path):
    from src.services import medicine_image_urls as mod
    from src.services.medicine_image_urls import medicine_has_ready_image

    manifest = tmp_path / "versions.json"
    manifest.write_text('{"イブA錠": "deadbeef"}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_VERSIONS_PATH", manifest)
    mod.invalidate_otc_image_versions_cache()

    assert medicine_has_ready_image({"product_name": "イブA錠"})
    assert medicine_has_ready_image({"product_name": "イブ"})
    assert not medicine_has_ready_image({"product_name": "存在しないテスト用製品XYZ"})


def test_resolve_otc_image_slug_alias_maps_ib_to_ib_a():
    from src.services.medicine_image_urls import resolve_medicine_image_slug

    assert resolve_medicine_image_slug({"product_name": "イブ"}) == "イブA錠"


def test_enrich_sets_image_url():
    row = enrich_medicine_image_url({"product_name": "カロナールA", "image_slug": "test"})
    assert row["image_url"] == "https://images.yutok.dev/otc/test.webp"
    assert row["product_image_url"] == row["image_url"]
    assert row["image_slug"] == "test"


def test_enrich_rewrites_stale_managed_cdn_url():
    stale = "https://images.yutok.dev/otc/スカイブブロンのどスプレー.webp"
    row = enrich_medicine_image_url(
        {"product_name": "スカイブブロンのどスプレー", "image_url": stale}
    )
    assert row["image_url"] != stale
    assert "%" in row["image_url"]
    assert "?v=" in row["image_url"]


def test_enrich_prefers_manifest_over_stale_row_version(monkeypatch, tmp_path):
    from src.services import medicine_image_urls as mod

    manifest = tmp_path / "versions.json"
    manifest.write_text('{"新スカイブブロンゴールド微粒": "26197a00"}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_VERSIONS_PATH", manifest)
    mod.invalidate_otc_image_versions_cache()

    row = enrich_medicine_image_url(
        {
            "product_name": "新スカイブブロンゴールド微粒",
            "manufacturer": "米田薬品工業",
            "image_version": "4616cbf7",
            "image_url": "https://images.yutok.dev/otc/%E6%96%B0%E3%82%B9%E3%82%AB%E3%82%A4%E3%83%96%E3%83%96%E3%83%AD%E3%83%B3%E3%82%B4%E3%83%BC%E3%83%AB%E3%83%89%E5%BE%AE%E7%B2%92.webp?v=4616cbf7",
        }
    )
    assert row["image_version"] == "26197a00"
    assert "26197a00" in row["image_url"]


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
