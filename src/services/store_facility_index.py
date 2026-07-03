"""
施設・小売チェーン名の正規化インデックス（商品インデックスとの照合分離用）。

data/store_inquiry_keyword_catalog.json の facilities / external_retail_chains /
retail_store_chains を単一の定義元とし、商品カタログ照合から施設名を除外する。
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_index_built = False
_facility_tokens: set[str] = set()
_external_chain_tokens: set[str] = set()
_all_store_locator_tokens: set[str] = set()
_token_to_label: dict[str, str] = {}


def _normalize_token(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    try:
        from src.core.scoring_utils import basic_normalize_text

        return basic_normalize_text(raw)
    except ImportError:
        return raw.lower()


def _register_label(label: str, *, bucket: str) -> None:
    norm = _normalize_token(label)
    if not norm or len(norm) < 2:
        return
    _token_to_label.setdefault(norm, label)
    if bucket == "external_chain":
        _external_chain_tokens.add(norm)
    else:
        _facility_tokens.add(norm)
    _all_store_locator_tokens.add(norm)


def ensure_facility_index() -> None:
    """遅延シングルトンで施設インデックスを構築する。"""
    global _index_built, _facility_tokens, _external_chain_tokens
    global _all_store_locator_tokens, _token_to_label
    if _index_built:
        return

    try:
        from src.core.dictionary_loader import load_store_inquiry_keyword_catalog

        catalog = load_store_inquiry_keyword_catalog()
    except Exception as exc:
        logger.warning("⚠️ 施設インデックス: カタログ読み込み失敗: %s", exc)
        catalog = {}

    facilities = (catalog.get("subtypes") or {}).get("facilities") or {}
    for cat in facilities.get("categories") or []:
        for label in cat.get("labels") or []:
            _register_label(str(label), bucket="facility")

    for label in catalog.get("external_retail_chains") or []:
        _register_label(str(label), bucket="external_chain")

    for label in catalog.get("retail_store_chains") or []:
        _register_label(str(label), bucket="facility")

    _index_built = True
    logger.info(
        "✅ 施設インデックス構築: facilities=%d external_chains=%d total=%d",
        len(_facility_tokens),
        len(_external_chain_tokens),
        len(_all_store_locator_tokens),
    )


def is_facility_name(text: str) -> bool:
    """正規化後の完全一致、または元ラベルそのものが施設・店舗チェーン名なら True。"""
    ensure_facility_index()
    raw = (text or "").strip()
    if not raw:
        return False
    norm = _normalize_token(raw)
    return norm in _all_store_locator_tokens or raw in _token_to_label.values()


def get_external_chain_labels() -> Tuple[str, ...]:
    """detect_external_chain_location_inquiry 用のチェーン名（表示順は不定）。"""
    ensure_facility_index()
    labels = [
        _token_to_label[n]
        for n in _external_chain_tokens
        if n in _token_to_label
    ]
    return tuple(dict.fromkeys(labels))


def find_facility_in_text(user_text: str) -> Optional[str]:
    """ユーザ入力に含まれる最長の施設・チェーン名（原文ラベル）。"""
    ensure_facility_index()
    norm_text = _normalize_token(user_text)
    if not norm_text:
        return None
    best: Optional[Tuple[int, str]] = None
    for norm, label in _token_to_label.items():
        if norm in norm_text:
            cand = (len(norm), label)
            if best is None or cand[0] > best[0]:
                best = cand
    return best[1] if best else None


def is_store_locator_query(user_text: str) -> bool:
    """
    施設・チェーン名 + 位置問い合わせヒントの組み合わせ。
    商品在庫ではなく店舗案内へ振り分けるべき入力。
    """
    t = user_text or ""
    location_hints = ("近く", "どこ", "ありますか", "近隣", "場所")
    if "ドラッグストア" in t and any(h in t for h in location_hints):
        return True
    if "薬局" in t and any(h in t for h in location_hints):
        if not _has_product_stock_context(t):
            return True
    label = find_facility_in_text(t)
    if label and any(h in t for h in location_hints):
        return True
    return False


def _has_product_stock_context(user_text: str) -> bool:
    stock_hints = ("在庫", "売", "買", "取り扱", "扱", "購入", "注文", "取り寄せ")
    return any(h in user_text for h in stock_hints)


def reset_facility_index_cache() -> None:
    """テスト用: インデックスキャッシュをクリア。"""
    global _index_built, _facility_tokens, _external_chain_tokens
    global _all_store_locator_tokens, _token_to_label
    _index_built = False
    _facility_tokens = set()
    _external_chain_tokens = set()
    _all_store_locator_tokens = set()
    _token_to_label = {}


def index_stats() -> dict[str, int]:
    ensure_facility_index()
    return {
        "facility_tokens": len(_facility_tokens),
        "external_chain_tokens": len(_external_chain_tokens),
        "total_tokens": len(_all_store_locator_tokens),
    }
