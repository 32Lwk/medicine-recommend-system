"""
成分抽出・重複チェック

candidate_scoring から分離（SRP改善）。
"""

import re
from itertools import combinations
from typing import Dict, List

from src.core.dictionary_loader import load_ingredient_dictionary
from src.core.recommendation_constants import RISK_INGREDIENTS_OVERLAP

# 成分抽出キャッシュ（extract_main_ingredients 用）
_ingredient_extraction_cache: Dict = {}
_max_ingredient_extraction_cache_size = 500


def extract_main_ingredients(ingredients: str, max_count: int = 3) -> List[str]:
    """成分表から主要成分を抽出し、比較用に正規化する（キャッシュ対応、表記ゆれ対応）"""
    if not ingredients or not isinstance(ingredients, str):
        return []

    cache_key = (ingredients, max_count)
    if cache_key in _ingredient_extraction_cache:
        return _ingredient_extraction_cache[cache_key]

    ingredient_mapping = {}
    try:
        for canonical_name, info in load_ingredient_dictionary().items():
            synonyms = info.get('synonyms', [])
            for synonym in synonyms:
                ingredient_mapping[synonym.lower()] = canonical_name.lower()
    except (NameError, AttributeError):
        ingredient_mapping = {}

    parts = re.split(r"[\n、,/，／・]+", ingredients)
    normalized = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        token_lower = token.lower()
        if token_lower in ingredient_mapping:
            normalized_token = ingredient_mapping[token_lower]
        else:
            normalized_token = token_lower
        if normalized_token not in normalized:
            normalized.append(normalized_token)
        if len(normalized) >= max_count:
            break

    if len(_ingredient_extraction_cache) >= _max_ingredient_extraction_cache_size:
        oldest_key = next(iter(_ingredient_extraction_cache))
        del _ingredient_extraction_cache[oldest_key]
    _ingredient_extraction_cache[cache_key] = normalized
    return normalized


def check_ingredient_overlap(medicines: List[Dict]) -> Dict:
    """
    推奨医薬品リスト内で成分重複をチェック（集合演算を使用）

    Args:
        medicines: 推奨医薬品のリスト（Dictのリスト）

    Returns:
        {
            "has_overlap": bool,
            "overlapping_ingredients": List[Dict],
            "affected_medicines": List[str],
            "highest_severity": str
        }
    """
    overlap_result = {
        "has_overlap": False,
        "overlapping_ingredients": [],
        "affected_medicines": [],
        "highest_severity": "blue"
    }
    if len(medicines) < 2:
        return overlap_result

    medicine_ingredient_sets = {}
    for medicine in medicines:
        product_name = medicine.get('product_name', '')
        ingredients_str = medicine.get('ingredients', '')
        if ingredients_str:
            ingredients_list = extract_main_ingredients(ingredients_str, max_count=20)
            ingredients_set = set(ing.lower() for ing in ingredients_list)
            medicine_ingredient_sets[product_name] = ingredients_set

    risk_ingredient_sets = {}
    for risk_name, risk_info in RISK_INGREDIENTS_OVERLAP.items():
        canonical = risk_info["canonical_name"].lower()
        synonyms = [s.lower() for s in risk_info.get("synonyms", [])]
        risk_set = {canonical} | set(synonyms)
        risk_ingredient_sets[risk_name] = {
            "ingredient_set": risk_set,
            "info": risk_info
        }

    checked_combinations = set()
    for (med1_name, ing_set1), (med2_name, ing_set2) in combinations(medicine_ingredient_sets.items(), 2):
        common_ingredients = ing_set1 & ing_set2
        if not common_ingredients:
            continue
        for risk_name, risk_data in risk_ingredient_sets.items():
            risk_set = risk_data["ingredient_set"]
            risk_info = risk_data["info"]
            overlapping_risk = common_ingredients & risk_set
            if overlapping_risk:
                overlap_key = (risk_name, tuple(sorted([med1_name, med2_name])))
                if overlap_key not in checked_combinations:
                    checked_combinations.add(overlap_key)
                    severity = risk_info.get("severity", "blue")
                    warning_msg = risk_info["warning_message"]
                    if severity == "red":
                        side_effect_msg = "（過剰摂取のリスクがあります。同時に服用しないでください）"
                    elif severity == "yellow":
                        if risk_info.get("category") == "antihistamine":
                            side_effect_msg = f"（同じ成分が含まれていますので、併用時は副作用（{risk_info.get('focus_side_effect', '眠気')}など）にご注意ください）"
                        else:
                            side_effect_msg = "（同じ成分が含まれていますので、併用時は副作用にご注意ください）"
                    else:
                        side_effect_msg = "（同じ成分が含まれていますので、用法用量をご確認ください）"
                    overlap_result["has_overlap"] = True
                    overlap_result["overlapping_ingredients"].append({
                        "ingredient_name": risk_name,
                        "warning_message": warning_msg,
                        "medicines": sorted([med1_name, med2_name]),
                        "side_effect_message": side_effect_msg,
                        "severity": severity
                    })
                    overlap_result["affected_medicines"].extend([med1_name, med2_name])

    if overlap_result["overlapping_ingredients"]:
        severities = [overlap.get("severity", "blue") for overlap in overlap_result["overlapping_ingredients"]]
        severity_order = {"red": 3, "yellow": 2, "blue": 1}
        highest_severity = max(severities, key=lambda s: severity_order.get(s, 0))
        overlap_result["highest_severity"] = highest_severity
    overlap_result["affected_medicines"] = list(set(overlap_result["affected_medicines"]))
    return overlap_result
