"""
ユーザー嗜好に基づく候補のスコアリング前除外（confidence >= 0.8）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.core.dictionary_loader import load_preference_keyword_catalog
from src.core.preference_merge import preference_field_confidence
from src.core.recommendation.pollen_rhinitis_scoring import (
    classify_pollen_rhinitis_product,
)

logger = logging.getLogger(__name__)


def _ingredients_match_groups(ingredients: str, group_names: List[str], catalog: Dict) -> bool:
    groups = catalog.get("ingredient_groups") or {}
    text = ingredients or ""
    for name in group_names:
        for token in groups.get(name, []):
            if token in text:
                return True
    return False


def filter_candidates_by_preferences(
    candidates: List[Dict],
    user_preferences: Optional[Dict[str, Any]],
    *,
    nlu_result: Optional[Dict] = None,
    user_info: Optional[Dict] = None,
) -> List[Dict]:
    if not candidates or not user_preferences:
        return candidates

    catalog = load_preference_keyword_catalog()
    exclude_min = float(catalog.get("exclude_apply_min_confidence", 0.8))
    rules = catalog.get("risk_exclude_rules") or []

    filtered: List[Dict] = []
    for candidate in candidates:
        exclude_reason = None
        ingredients = str(candidate.get("ingredients", ""))

        for rule in rules:
            when = rule.get("when") or {}
            field = when.get("field")
            min_conf = float(when.get("min_confidence", exclude_min))
            if not field or not user_preferences.get(field):
                continue
            if preference_field_confidence(user_preferences, field) < min_conf:
                continue

            ing_groups = rule.get("exclude_ingredient_groups") or []
            if ing_groups and _ingredients_match_groups(ingredients, ing_groups, catalog):
                exclude_reason = f"preference_exclude:{field}:ingredient"
                break

            product_classes = rule.get("exclude_product_classes") or []
            if product_classes:
                pclass = classify_pollen_rhinitis_product(candidate)
                if pclass in product_classes:
                    exclude_reason = f"preference_exclude:{field}:class_{pclass}"
                    break

        if exclude_reason:
            logger.info(
                "🚫 嗜好除外: %s (%s)",
                candidate.get("product_name", ""),
                exclude_reason,
            )
            continue
        filtered.append(candidate)

    return filtered
