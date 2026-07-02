"""
店舗商品カタログの正規化インデックス（起動時構築・Aho-Corasick 照合）

~20k 商品名を正規化・重複排除し、リクエストごとの全件線形スキャンを避ける。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MIN_TOKEN_LEN = 2
_index_built = False
_token_to_info: Dict[str, Dict[str, str]] = {}
_automaton: Any = None
_ac_available: Optional[bool] = None
_fallback_warned = False
_raw_category_count = 0
_unique_token_count = 0


def _normalize_token(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    try:
        from src.core.scoring_utils import basic_normalize_text

        return basic_normalize_text(raw)
    except ImportError:
        return raw.lower()


def _load_product_categories() -> Dict[str, Any]:
    try:
        from src import PROJECT_ROOT

        path = os.path.join(PROJECT_ROOT, "data", "store_products.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("⚠️ 商品リストの読み込みに失敗: %s", exc)
        return {}


def _register_token(
    norm: str,
    *,
    category: str,
    subcategory: str,
    product: str,
    matched_keyword: str,
) -> None:
    global _unique_token_count
    if not norm or len(norm) < _MIN_TOKEN_LEN:
        return
    try:
        from src.services.store_facility_index import is_facility_name

        if is_facility_name(norm) or is_facility_name(matched_keyword):
            return
    except ImportError:
        pass
    if norm in _token_to_info:
        return
    _token_to_info[norm] = {
        "category": category,
        "subcategory": subcategory,
        "product": product,
        "matched_keyword": matched_keyword,
    }
    _unique_token_count += 1


def _build_token_index(categories: Dict[str, Any]) -> None:
    for category_name, category_data in categories.items():
        subcategories = category_data.get("subcategories", {})
        for subcategory_name, subcategory_data in subcategories.items():
            for product in subcategory_data.get("products", []):
                norm = _normalize_token(product)
                _register_token(
                    norm,
                    category=category_name,
                    subcategory=subcategory_name,
                    product=product,
                    matched_keyword=product,
                )
            for brand in subcategory_data.get("brands", []):
                norm = _normalize_token(brand)
                _register_token(
                    norm,
                    category=category_name,
                    subcategory=subcategory_name,
                    product=brand,
                    matched_keyword=brand,
                )


def _try_build_automaton() -> None:
    global _automaton, _ac_available
    try:
        import ahocorasick

        automaton = ahocorasick.Automaton()
        for idx, (norm, info) in enumerate(_token_to_info.items()):
            automaton.add_word(norm, (idx, norm, info))
        automaton.make_automaton()
        _automaton = automaton
        _ac_available = True
    except ImportError:
        _automaton = None
        _ac_available = False


def ensure_product_index() -> None:
    """遅延シングルトンで商品インデックスを構築する。"""
    global _index_built, _raw_category_count
    if _index_built:
        return
    categories = _load_product_categories()
    _raw_category_count = len(categories)
    _build_token_index(categories)
    _try_build_automaton()
    _index_built = True
    ac_label = "AC" if _ac_available else "linear"
    logger.info(
        "✅ 商品インデックス構築: %dカテゴリ → %dユニークトークン (%s)",
        _raw_category_count,
        _unique_token_count,
        ac_label,
    )


def _match_linear(norm_text: str) -> Optional[Dict[str, str]]:
    best: Optional[Tuple[int, Dict[str, str]]] = None
    for norm, info in _token_to_info.items():
        if norm in norm_text:
            cand = (len(norm), info)
            if best is None or cand[0] > best[0]:
                best = cand
    return best[1] if best else None


def _match_automaton(norm_text: str) -> Optional[Dict[str, str]]:
    if _automaton is None:
        return _match_linear(norm_text)
    best: Optional[Tuple[int, Dict[str, str]]] = None
    for _end, (_idx, norm, info) in _automaton.iter(norm_text):
        cand = (len(norm), info)
        if best is None or cand[0] > best[0]:
            best = cand
    return best[1] if best else None


def classify_product_category(user_text: str) -> Optional[Dict]:
    """
    正規化テキストに対する商品カテゴリ照合（O(text)）。

    Returns:
        検出時: category / subcategory / product / matched_keyword
    """
    ensure_product_index()
    if not _token_to_info:
        return None

    norm_text = _normalize_token(user_text)
    if not norm_text:
        return None

    global _fallback_warned
    if _ac_available is False and not _fallback_warned:
        logger.warning(
            "⚠️ pyahocorasick 未導入のため商品照合は線形フォールバック"
        )
        _fallback_warned = True

    info = _match_automaton(norm_text)
    if info:
        try:
            from src.services.store_facility_index import is_facility_name

            matched = info.get("matched_keyword") or info.get("product") or ""
            if is_facility_name(matched):
                return None
        except ImportError:
            pass
        logger.info(
            "🔍 商品カテゴリ検出: %s > %s > %s",
            info["category"],
            info["subcategory"],
            info["product"],
        )
        return dict(info)
    return None


def index_stats() -> Dict[str, int]:
    """テスト・診断用のインデックス統計。"""
    ensure_product_index()
    return {
        "raw_categories": _raw_category_count,
        "unique_tokens": _unique_token_count,
    }


def reset_product_index_cache() -> None:
    """テスト用: 商品インデックスキャッシュをクリア。"""
    global _index_built, _token_to_info, _automaton, _ac_available
    global _fallback_warned, _raw_category_count, _unique_token_count
    _index_built = False
    _token_to_info = {}
    _automaton = None
    _ac_available = None
    _fallback_warned = False
    _raw_category_count = 0
    _unique_token_count = 0
