"""風邪入力の症状展開とチッププロンプト判定（RECO_COLD_NLU_V2）。"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional

from src.services.medicine_discovery_routing import (
    has_medicine_discovery_intent,
    has_sports_medicine_context,
)

COLD_KEYWORD = "風邪"
COLD_EXPAND_SYMPTOMS = (
    "発熱",
    "咳",
    "のどの痛み",
    "鼻水",
    "鼻づまり",
    "頭痛",
    "関節痛",
)

_COLD_CHIP_OPTIONS = (
    ("cold_fever", "発熱", "発熱があります"),
    ("cold_cough", "咳", "咳が出ます"),
    ("cold_throat", "のどの痛み", "のどが痛いです"),
    ("cold_runny", "鼻水", "鼻水が出ます"),
    ("cold_stuffy", "鼻づまり", "鼻づまりがあります"),
    ("cold_headache", "頭痛", "頭痛があります"),
    ("cold_joint", "関節痛", "関節痛があります"),
)

_SPORTS_SKIP_MARKERS = ("大会", "水泳", "泳", "競技", "レース", "試合", "プール", "競泳")


def _symptom_names(nlu_result: Optional[Dict[str, Any]]) -> List[str]:
    names: list[str] = []
    for s in (nlu_result or {}).get("symptoms") or []:
        if isinstance(s, dict):
            name = str(s.get("name") or "").strip()
        else:
            name = str(s or "").strip()
        if name:
            names.append(name)
    return names


def should_prompt_cold_symptoms(
    user_text: str,
    nlu_result: Optional[Dict[str, Any]] = None,
) -> bool:
    text = (user_text or "").strip()
    if COLD_KEYWORD not in text:
        return False
    if re.search(
        r"(?:何|なに)が(?:いい|ええ|よい)|市販|薬.*(?:ええ|いい|よい|ある)",
        text,
    ):
        return False
    if len(_symptom_names(nlu_result)) > 1:
        return False
    if has_sports_medicine_context(text) and (
        has_medicine_discovery_intent(text)
        or any(m in text for m in _SPORTS_SKIP_MARKERS)
    ):
        return False
    extra_hints = (
        "痛", "熱", "咳", "鼻", "頭", "関節", "のど", "喉", "発熱", "だる", "寒気",
    )
    hits = sum(1 for h in extra_hints if h in text)
    return hits <= 2


def cold_symptom_chip_actions() -> List[Dict[str, str]]:
    return [
        {"id": opt_id, "label": label, "postback_text": postback}
        for opt_id, label, postback in _COLD_CHIP_OPTIONS
    ]


def merge_cold_symptoms(nlu_result: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """「風邪」キーワード時にルール展開症状を GPT 結果へマージする。"""
    if COLD_KEYWORD not in (user_text or ""):
        return nlu_result
    if should_prompt_cold_symptoms(user_text, nlu_result):
        return nlu_result

    merged = copy.deepcopy(nlu_result)
    existing = set(_symptom_names(merged))
    symptoms = list(merged.get("symptoms") or [])
    for name in COLD_EXPAND_SYMPTOMS:
        if name in existing:
            continue
        symptoms.append({"name": name, "severity": "中等度", "source": "cold_rule_expand"})
        existing.add(name)
    merged["symptoms"] = symptoms
    return merged
