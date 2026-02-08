"""
症状パターンマッチングとキャッシュ（SRP: 1ファイル＝1責務）

match_symptom_pattern を提供。rule_based_recommendation から import して利用する。
"""
import logging
import os
from typing import Dict, Optional

from src.core.recommendation_constants import SYMPTOM_PATTERN_OPTIMIZATION

logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# 症状パターンマッチングキャッシュ
_symptom_pattern_cache: Dict = {}
_max_symptom_pattern_cache_size = 200


def match_symptom_pattern(nlu_result: Dict) -> Optional[Dict]:
    """
    症状パターンをマッチングして、最適化情報を返す（キャッシュ対応）
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return None

    symptom_names = [s.get("name") for s in symptoms]
    normalized_symptom_names = []
    symptom_mapping = {
        "疲労感": "だるさ",
        "倦怠感": "だるさ",
        "疲れ": "だるさ",
        "だるい": "だるさ",
        "生理不順": "月経不順",
        "生理異常": "月経不順",
    }
    for name in symptom_names:
        normalized_name = symptom_mapping.get(name, name)
        if normalized_name != name:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状名を正規化: {name} → {normalized_name}")
        normalized_symptom_names.append(normalized_name)

    symptom_set = frozenset(normalized_symptom_names)
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"🔍 症状パターンマッチング: 元の症状={symptom_names}, 正規化後={list(symptom_set)}")

    cache_key = tuple(sorted(symptom_set))
    if cache_key in _symptom_pattern_cache:
        result = _symptom_pattern_cache[cache_key]
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            if result:
                logger.debug(f"✅ 症状パターンマッチング（キャッシュ）: {list(symptom_set)} → マッチ")
        return result

    if symptom_set in SYMPTOM_PATTERN_OPTIMIZATION:
        result = SYMPTOM_PATTERN_OPTIMIZATION[symptom_set]
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"✅ 症状パターンマッチング（完全一致）: {list(symptom_set)} → マッチ")
    else:
        result = None
        for pattern_symptoms, pattern_info in SYMPTOM_PATTERN_OPTIMIZATION.items():
            if symptom_set.issubset(pattern_symptoms):
                result = pattern_info
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"✅ 症状パターンマッチング（部分一致）: {list(symptom_set)} ⊆ {list(pattern_symptoms)} → マッチ")
                break
        if result is None and (DEBUG_MODE or logger.level <= logging.DEBUG):
            logger.debug(f"❌ 症状パターンマッチング: {list(symptom_set)} → マッチなし")

    if len(_symptom_pattern_cache) >= _max_symptom_pattern_cache_size:
        oldest_key = next(iter(_symptom_pattern_cache))
        del _symptom_pattern_cache[oldest_key]

    _symptom_pattern_cache[cache_key] = result
    return result
