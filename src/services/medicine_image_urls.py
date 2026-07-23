"""OTC 商品画像 URL 解決（Cloudflare R2 CDN / 明示 URL）。"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Mapping

from config.aws_features import get_medicine_image_cdn_base

_IMAGE_URL_KEYS = ("image_url", "imageUrl", "hero_url", "product_image_url")
_SLUG_KEYS = ("image_slug", "product_image_slug")
_JAN_KEYS = ("jan", "jan_code", "JAN", "product_id")


def _pick_str(data: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def slugify_product_name(name: str, manufacturer: str = "") -> str:
    """
    R2 オブジェクトキー用スラッグ（otc/{slug}.webp）。
    日本語製品名は読みやすさより安定性を優先し、空になった場合は短 hash。
    """
    raw = unicodedata.normalize("NFKC", (name or "").strip())
    mfr = unicodedata.normalize("NFKC", (manufacturer or "").strip())
    combined = f"{raw}|{mfr}" if mfr else raw
    if not combined.replace("|", "").strip():
        return ""

    slug = re.sub(r"\s+", "-", raw)
    slug = re.sub(r"[^\w\-一-龥ぁ-んァ-ヶ]", "", slug)
    slug = slug.strip("-")
    if len(slug) >= 2:
        return slug[:80]
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
    return f"p-{digest}"


def resolve_medicine_image_slug(medicine: Mapping[str, Any]) -> str:
    explicit = _pick_str(medicine, _SLUG_KEYS)
    if explicit:
        return explicit
    jan = _pick_str(medicine, _JAN_KEYS)
    if jan:
        return re.sub(r"[^\w\-]", "", jan)
    name = _pick_str(medicine, ("product_name", "name"))
    manufacturer = _pick_str(medicine, ("manufacturer", "maker"))
    return slugify_product_name(name, manufacturer)


def resolve_medicine_image_url(medicine: Mapping[str, Any] | None) -> str | None:
    if not medicine:
        return None
    for key in _IMAGE_URL_KEYS:
        val = (medicine.get(key) or "").strip()
        if val.startswith("https://") or val.startswith("http://"):
            return val
    base = get_medicine_image_cdn_base()
    if not base:
        return None
    slug = resolve_medicine_image_slug(medicine)
    if not slug:
        return None
    ext = str(medicine.get("image_ext") or "webp").lstrip(".") or "webp"
    return f"{base}{slug}.{ext}"


def enrich_medicine_image_url(medicine: dict[str, Any]) -> dict[str, Any]:
    """image_url / product_image_url を CDN 規則で補完（既存 https は尊重）。"""
    row = dict(medicine)
    url = resolve_medicine_image_url(row)
    if url:
        row.setdefault("image_url", url)
        row.setdefault("product_image_url", url)
    return row
