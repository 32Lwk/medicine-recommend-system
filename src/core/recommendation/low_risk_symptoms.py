"""低リスク症状の推奨補助（p3-headache-reco）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.core.recommendation_constants import (
    CAUTION_DEFER_SINGLE_SYMPTOMS,
    MAJOR_ANALGESIC_MEDICINES,
    RED_FLAG_SYMPTOMS,
)
from src.core.scoring_utils import normalize_medicine_name_to_hankaku

_PEDIATRIC_HINTS = ("子ども", "子供", "こども", "赤ちゃん", "幼児", "小学生", "児")


def _symptom_names(nlu_result: Optional[Dict[str, Any]]) -> list[str]:
    return [
        str(s.get("name"))
        for s in (nlu_result or {}).get("symptoms", [])
        if s.get("name")
    ]


def has_headache_red_flag(user_text: str = "") -> bool:
    text = (user_text or "").strip()
    if not text:
        return False
    for keywords in RED_FLAG_SYMPTOMS.values():
        for kw in keywords:
            if kw in text:
                return True
    return False


def has_pediatric_context_without_age(
    user_text: str = "",
    user_info: Optional[Dict[str, Any]] = None,
) -> bool:
    if (user_info or {}).get("age") is not None:
        return False
    text = user_text or ""
    return any(h in text for h in _PEDIATRIC_HINTS)


def is_caution_defer_single_symptom(nlu_result: Optional[Dict[str, Any]]) -> bool:
    """めまい等、単独では OTC 推奨を保留する症状か。"""
    names = _symptom_names(nlu_result)
    return len(names) == 1 and names[0] in CAUTION_DEFER_SINGLE_SYMPTOMS


def is_low_risk_headache_only(
    nlu_result: Optional[Dict[str, Any]],
    user_text: str = "",
    user_info: Optional[Dict[str, Any]] = None,
) -> bool:
    """単独頭痛・赤旗なし・小児文脈なしの低リスク頭痛か。"""
    names = _symptom_names(nlu_result)
    if len(names) != 1 or names[0] != "頭痛":
        return False
    if has_headache_red_flag(user_text):
        return False
    if has_pediatric_context_without_age(user_text, user_info):
        return False
    return True


def is_major_analgesic_medicine(medicine: Dict[str, Any]) -> bool:
    product_name_norm = normalize_medicine_name_to_hankaku(
        str(medicine.get("product_name") or "")
    )
    return any(
        normalize_medicine_name_to_hankaku(m) in product_name_norm
        for m in MAJOR_ANALGESIC_MEDICINES
    )


def filter_headache_analgesics_for_unknown_age(medicines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """年齢未入力時でも主要解熱鎮痛薬を残す（その他は従来の年齢制限フィルタ）。"""
    kept: list[Dict[str, Any]] = []
    for med in medicines:
        if is_major_analgesic_medicine(med) and "解熱鎮痛薬" in str(
            med.get("medicine_type") or ""
        ):
            kept.append(med)
            continue
        restriction = str(med.get("age_restriction") or "")
        match = re.search(r"(\d+)歳", restriction)
        if match and int(match.group(1)) >= 12:
            continue
        kept.append(med)
    return kept
