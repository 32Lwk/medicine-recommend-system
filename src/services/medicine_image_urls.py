"""OTC 商品画像 URL 解決（Cloudflare R2 CDN / 明示 URL）。"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

from config.aws_features import get_medicine_image_cdn_base

_IMAGE_URL_KEYS = ("image_url", "imageUrl", "hero_url", "product_image_url")
_SLUG_KEYS = ("image_slug", "product_image_slug")
_JAN_KEYS = ("jan", "jan_code", "JAN", "product_id")
_VERSIONS_PATH = Path(__file__).resolve().parents[2] / "data" / "otc_image_versions.json"
_versions_cache: dict[str, str] | None = None
_versions_cache_mtime: float | None = None

# 通称・短い製品名 → R2 上の画像スラッグ（ブランド名と object key が異なる場合）
OTC_IMAGE_SLUG_ALIASES: dict[str, str] = {
    "イブ": "イブA錠",
}


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


def invalidate_otc_image_versions_cache() -> None:
    global _versions_cache, _versions_cache_mtime
    _versions_cache = None
    _versions_cache_mtime = None


def _manifest_version_for_slug(slug: str) -> str:
    if not slug:
        return ""
    return load_otc_image_versions().get(slug, "")


def _resolve_image_version(slug: str, row_version: str = "") -> str:
    """manifest の hash を優先（画像差し替え後もプロセス再起動なしで反映）。"""
    manifest_version = _manifest_version_for_slug(slug)
    if manifest_version:
        return manifest_version
    return (row_version or "").strip()


def load_otc_image_versions() -> dict[str, str]:
    """slug -> content hash（キャッシュバスティング用）。"""
    global _versions_cache, _versions_cache_mtime
    try:
        mtime = _VERSIONS_PATH.stat().st_mtime
    except OSError:
        mtime = None
    if _versions_cache is not None and _versions_cache_mtime == mtime:
        return _versions_cache
    try:
        raw = json.loads(_VERSIONS_PATH.read_text(encoding="utf-8"))
        _versions_cache = {str(k): str(v) for k, v in raw.items() if v}
        _versions_cache_mtime = mtime
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        _versions_cache = {}
        _versions_cache_mtime = mtime
    return _versions_cache


def content_hash_for_image(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:8]


def record_otc_image_version(slug: str, body: bytes) -> str:
    """画像更新時に manifest を更新し、短 hash を返す。"""
    version = content_hash_for_image(body)
    versions: dict[str, str] = {}
    if _VERSIONS_PATH.is_file():
        try:
            loaded = json.loads(_VERSIONS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                versions = {str(k): str(v) for k, v in loaded.items() if v}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            versions = {}
    versions[slug] = version
    _VERSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _VERSIONS_PATH.write_text(
        json.dumps(versions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    invalidate_otc_image_versions_cache()
    return version


def resolve_otc_image_slug_alias(slug: str) -> str:
    """R2 画像キー用スラッグへ通称を正規化する。"""
    key = (slug or "").strip()
    if not key:
        return ""
    return OTC_IMAGE_SLUG_ALIASES.get(key, key)


def resolve_medicine_image_slug(medicine: Mapping[str, Any]) -> str:
    explicit = _pick_str(medicine, _SLUG_KEYS)
    if explicit:
        return resolve_otc_image_slug_alias(explicit)
    jan = _pick_str(medicine, _JAN_KEYS)
    if jan:
        return resolve_otc_image_slug_alias(re.sub(r"[^\w\-]", "", jan))
    name = _pick_str(medicine, ("product_name", "name"))
    manufacturer = _pick_str(medicine, ("manufacturer", "maker"))
    return resolve_otc_image_slug_alias(slugify_product_name(name, manufacturer))


def build_medicine_image_cdn_url(
    base: str,
    slug: str,
    ext: str = "webp",
    *,
    version: str | None = None,
) -> str:
    """
    CDN URL を組み立てる。
    日本語 slug は percent-encode し、更新時は ?v=hash で Cloudflare キャッシュを回避する。
    """
    base_norm = base.rstrip("/") + "/"
    encoded_slug = quote(slug, safe="")
    ext_norm = ext.lstrip(".") or "webp"
    url = f"{base_norm}{encoded_slug}.{ext_norm}"
    v = version or load_otc_image_versions().get(slug)
    if v:
        url = f"{url}?v={quote(v, safe='')}"
    return url


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
    version = _resolve_image_version(slug, _pick_str(medicine, ("image_version",)))
    return build_medicine_image_cdn_url(base, slug, ext, version=version or None)


def _is_managed_cdn_url(url: str) -> bool:
    base = get_medicine_image_cdn_base()
    return bool(base and url.startswith(base))


def medicine_has_ready_image(medicine: Mapping[str, Any] | None) -> bool:
    """otc_image_versions 登録済み、または管理外 https URL がある場合 True。"""
    if not medicine:
        return False
    for key in _IMAGE_URL_KEYS:
        val = str(medicine.get(key) or "").strip()
        if val.startswith("https://") or val.startswith("http://"):
            if not _is_managed_cdn_url(val):
                return True
    slug = resolve_medicine_image_slug(medicine)
    if slug and slug in load_otc_image_versions():
        return True
    return False


def enrich_medicine_image_url(medicine: dict[str, Any]) -> dict[str, Any]:
    """image_url / product_image_url を CDN 規則で補完（外部 https は尊重）。"""
    row = dict(medicine)
    slug = resolve_medicine_image_slug(row)
    version = _resolve_image_version(slug, _pick_str(row, ("image_version",)))
    if version:
        row["image_version"] = version
    else:
        row.pop("image_version", None)

    explicit = ""
    for key in _IMAGE_URL_KEYS:
        val = (row.get(key) or "").strip()
        if val.startswith("https://") or val.startswith("http://"):
            explicit = val
            break

    if explicit and not _is_managed_cdn_url(explicit):
        return row

    base = get_medicine_image_cdn_base()
    if not base or not slug:
        return row

    ext = str(row.get("image_ext") or "webp").lstrip(".") or "webp"
    url = build_medicine_image_cdn_url(base, slug, ext, version=version or None)
    row["image_url"] = url
    row["product_image_url"] = url
    if slug:
        row["image_slug"] = slug
    return row
