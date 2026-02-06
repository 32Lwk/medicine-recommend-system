"""
辞書データのローダー

JSONファイルから INGREDIENT_DICTIONARY, SYMPTOM_DICTIONARY を読み込む。
キャッシュ付きで同一プロセス内での重複読み込みを避ける。
"""
import json
import os
from typing import Dict, Any, Optional

from src import PROJECT_ROOT

_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
_INGREDIENT_PATH = os.path.join(_DATA_DIR, "ingredient_dictionary.json")
_SYMPTOM_PATH = os.path.join(_DATA_DIR, "symptom_dictionary.json")

_cached_ingredient: Optional[Dict[str, Any]] = None
_cached_symptom: Optional[Dict[str, Any]] = None


def load_ingredient_dictionary() -> Dict[str, Any]:
    """成分辞書をJSONから読み込む（キャッシュ付き）"""
    global _cached_ingredient
    if _cached_ingredient is not None:
        return _cached_ingredient
    with open(_INGREDIENT_PATH, 'r', encoding='utf-8') as f:
        _cached_ingredient = json.load(f)
    return _cached_ingredient


def load_symptom_dictionary() -> Dict[str, Any]:
    """症状辞書をJSONから読み込む（キャッシュ付き）"""
    global _cached_symptom
    if _cached_symptom is not None:
        return _cached_symptom
    with open(_SYMPTOM_PATH, 'r', encoding='utf-8') as f:
        _cached_symptom = json.load(f)
    return _cached_symptom


def clear_cache() -> None:
    """キャッシュをクリア（テスト用）"""
    global _cached_ingredient, _cached_symptom
    _cached_ingredient = None
    _cached_symptom = None
