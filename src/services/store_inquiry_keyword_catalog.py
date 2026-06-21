"""
StoreInquiryAgent 向けキーワードカタログの読み込みと派生インデックス。

data/store_inquiry_keyword_catalog.json を単一の定義元とし、
ルーティング候補・文脈ゲート・施設名マッチに必要なリストを構築する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

from src.core.dictionary_loader import load_store_inquiry_keyword_catalog

logger = logging.getLogger(__name__)

_cached: Optional["StoreInquiryKeywords"] = None


@dataclass(frozen=True)
class StoreInquiryKeywords:
    spatial_keywords: List[str]
    location_question_keywords: List[str]
    store_scoped_keywords: List[str]
    store_location_bare_keywords: FrozenSet[str]
    store_inquiry_context_keywords: List[str]
    toilet_keywords: List[str]
    store_location_inside: List[str]
    store_location_outside: List[str]
    symptom_keywords_for_toilet: List[str]
    symptom_keywords: List[str]
    store_inquiry_keywords: List[str]
    store_inquiry_context_dependent_keywords: List[str]
    lost_and_found_keywords: List[str]
    inventory_inquiry_keywords: List[str]
    facility_names: List[str]
    facility_type_keywords: List[str]
    facility_names_ambiguous: FrozenSet[str]
    tax_free_keywords: List[str]
    tourism_keywords: List[str]
    business_hours_keywords: List[str]
    payment_keywords: List[str]
    parking_keywords: List[str]
    services_keywords: List[str]
    subtype_routing_tags: Dict[str, str] = field(default_factory=dict)
    subtype_require_store_scope: Dict[str, bool] = field(default_factory=dict)
    subtype_require_spatial_or_location: Dict[str, bool] = field(default_factory=dict)


def _labels_from_facility_categories(
    categories: List[dict],
    *,
    ambiguous: Optional[bool] = None,
) -> List[str]:
    labels: List[str] = []
    for cat in categories:
        if ambiguous is not None and bool(cat.get("ambiguous")) != ambiguous:
            continue
        labels.extend(cat.get("labels") or [])
    return labels


def _build_from_catalog(catalog: dict) -> StoreInquiryKeywords:
    context = catalog.get("context") or {}
    store_location = catalog.get("store_location") or {}
    medicine_priority = catalog.get("medicine_priority_keywords") or {}
    subtypes = catalog.get("subtypes") or {}

    facilities = subtypes.get("facilities") or {}
    facility_categories = facilities.get("categories") or []

    facility_names = _labels_from_facility_categories(facility_categories)
    facility_type_keywords = _labels_from_facility_categories(
        facility_categories, ambiguous=False
    )
    facility_names_ambiguous = frozenset(
        _labels_from_facility_categories(facility_categories, ambiguous=True)
    )

    subtype_routing_tags: Dict[str, str] = {}
    subtype_require_store_scope: Dict[str, bool] = {}
    subtype_require_spatial_or_location: Dict[str, bool] = {}

    for name, cfg in subtypes.items():
        if not isinstance(cfg, dict):
            continue
        tag = cfg.get("routing_tag")
        if tag:
            subtype_routing_tags[name] = str(tag)
        if cfg.get("require_store_scope"):
            subtype_require_store_scope[name] = True
        if cfg.get("requires_spatial_or_location_question"):
            subtype_require_spatial_or_location[name] = True

    store_inquiry = subtypes.get("store_inquiry") or {}

    return StoreInquiryKeywords(
        spatial_keywords=list(context.get("spatial_keywords") or []),
        location_question_keywords=list(context.get("location_question_keywords") or []),
        store_scoped_keywords=list(context.get("store_scoped_keywords") or []),
        store_location_bare_keywords=frozenset(context.get("store_location_bare_keywords") or []),
        store_inquiry_context_keywords=list(context.get("store_inquiry_context_keywords") or []),
        toilet_keywords=list(context.get("toilet_keywords") or []),
        store_location_inside=list(store_location.get("inside") or []),
        store_location_outside=list(store_location.get("outside") or []),
        symptom_keywords_for_toilet=list(
            medicine_priority.get("symptom_keywords_for_toilet") or []
        ),
        symptom_keywords=list(medicine_priority.get("symptom_keywords") or []),
        store_inquiry_keywords=list(store_inquiry.get("keywords") or []),
        store_inquiry_context_dependent_keywords=list(
            store_inquiry.get("context_dependent_keywords") or []
        ),
        lost_and_found_keywords=list((subtypes.get("lost_and_found") or {}).get("keywords") or []),
        inventory_inquiry_keywords=list((subtypes.get("inventory") or {}).get("keywords") or []),
        facility_names=facility_names,
        facility_type_keywords=facility_type_keywords,
        facility_names_ambiguous=facility_names_ambiguous,
        tax_free_keywords=list((subtypes.get("tax_free") or {}).get("keywords") or []),
        tourism_keywords=list((subtypes.get("tourism") or {}).get("keywords") or []),
        business_hours_keywords=list((subtypes.get("business_hours") or {}).get("keywords") or []),
        payment_keywords=list((subtypes.get("payment") or {}).get("keywords") or []),
        parking_keywords=list((subtypes.get("parking") or {}).get("keywords") or []),
        services_keywords=list((subtypes.get("services") or {}).get("keywords") or []),
        subtype_routing_tags=subtype_routing_tags,
        subtype_require_store_scope=subtype_require_store_scope,
        subtype_require_spatial_or_location=subtype_require_spatial_or_location,
    )


def get_store_inquiry_keywords() -> StoreInquiryKeywords:
    global _cached
    if _cached is None:
        try:
            catalog = load_store_inquiry_keyword_catalog()
            _cached = _build_from_catalog(catalog)
            logger.info(
                "✅ 店舗案内キーワードカタログを読み込みました: "
                "facilities=%d labels, subtypes=%d",
                len(_cached.facility_names),
                len(_cached.subtype_routing_tags),
            )
        except Exception as exc:
            logger.warning("⚠️ 店舗案内キーワードカタログの読み込みに失敗: %s", exc)
            _cached = _build_from_catalog({})
    return _cached


def reset_store_inquiry_keyword_cache() -> None:
    """テスト用: カタログキャッシュをクリア。"""
    global _cached
    _cached = None
