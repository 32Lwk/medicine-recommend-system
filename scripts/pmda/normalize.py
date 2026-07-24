"""PMDA 取得データの正規化（成分名・リスクレベル・ペア統一）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from scripts.pmda.common import normalize_text

INTERACTION_LEVEL_MAP = (
    (re.compile(r"併用禁忌|禁忌|重大|禁止|高リスク", re.I), "高"),
    (re.compile(r"併用注意|注意|中程度|中リスク", re.I), "中"),
    (re.compile(r"軽度|低リスク|情報なし", re.I), "低"),
)

SIDE_EFFECT_LEVEL_MAP = (
    (re.compile(r"重大|高リスク|重篤", re.I), "高"),
    (re.compile(r"中等度|中程度|中リスク", re.I), "中"),
    (re.compile(r"軽度|低リスク|まれ", re.I), "低"),
)


def map_interaction_level(raw: str, default: str = "中") -> str:
    text = normalize_text(raw)
    if text in ("高", "中", "低"):
        return text
    for pattern, level in INTERACTION_LEVEL_MAP:
        if pattern.search(text):
            return level
    return default


def map_side_effect_level(raw: str, default: str = "中") -> str:
    text = normalize_text(raw)
    if text in ("高", "中", "低"):
        return text
    for pattern, level in SIDE_EFFECT_LEVEL_MAP:
        if pattern.search(text):
            return level
    return default


def canonical_pair(a: str, b: str) -> Tuple[str, str]:
    left, right = normalize_text(a), normalize_text(b)
    if left > right:
        left, right = right, left
    return left, right


def pair_key(a: str, b: str) -> str:
    left, right = canonical_pair(a, b)
    return f"{left}|||{right}"


def normalize_interaction_row(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    a = normalize_text(str(row.get("成分A") or row.get("ingredient_a") or ""))
    b = normalize_text(str(row.get("成分B") or row.get("ingredient_b") or ""))
    if not a or not b or a == b:
        return None
    a, b = canonical_pair(a, b)
    level = map_interaction_level(str(row.get("相互作用レベル") or row.get("risk_level") or ""))
    desc = normalize_text(str(row.get("説明") or row.get("description") or ""))
    if not desc:
        desc = f"{a}と{b}の併用に注意が必要です（PMDA 添付文書相互作用参照）。"
    out = {
        "成分A": a,
        "成分B": b,
        "相互作用レベル": level,
        "説明": desc,
    }
    source = normalize_text(str(row.get("出典") or row.get("source") or ""))
    if source:
        out["出典"] = source
    updated = normalize_text(str(row.get("pmda_updated_at") or row.get("updated_at") or ""))
    if updated:
        out["pmda_updated_at"] = updated
    iid = normalize_text(str(row.get("interaction_id") or row.get("id") or ""))
    if iid:
        out["interaction_id"] = iid
    return out


def normalize_side_effect_row(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    ingredient = normalize_text(str(row.get("成分名") or row.get("ingredient") or ""))
    if not ingredient:
        return None
    level = map_side_effect_level(str(row.get("副作用レベル") or row.get("side_effect_level") or ""))
    symptoms = normalize_text(str(row.get("副作用症状") or row.get("symptoms") or ""))
    contraind = normalize_text(str(row.get("禁忌条件") or row.get("contraindications") or ""))
    if not symptoms:
        symptoms = "添付文書の副作用項参照（PMDA）"
    out = {
        "成分名": ingredient,
        "副作用レベル": level,
        "副作用症状": symptoms,
        "禁忌条件": contraind,
    }
    source = normalize_text(str(row.get("出典") or row.get("source") or ""))
    if source:
        out["出典"] = source
    return out


def normalize_otc_product_row(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    product = normalize_text(str(row.get("製品名") or row.get("product_name") or ""))
    if not product:
        return None
    out = {
        "製品名": product,
        "メーカー名": normalize_text(str(row.get("メーカー名") or row.get("manufacturer") or "")),
        "分類": normalize_text(str(row.get("分類") or row.get("classification") or "")),
        "医薬品の種類": normalize_text(str(row.get("医薬品の種類") or row.get("medicine_type") or "")),
        "効能効果": normalize_text(str(row.get("効能効果") or row.get("efficacy") or "")),
        "用法用量": normalize_text(str(row.get("用法用量") or row.get("usage") or "")),
        "年齢制限": normalize_text(str(row.get("年齢制限") or row.get("age_restriction") or "")),
        "成分": normalize_text(str(row.get("成分") or row.get("ingredients") or "")),
        "禁止物質あり": normalize_text(str(row.get("禁止物質あり") or row.get("doping_prohibited") or "")),
        "競技会区分": normalize_text(str(row.get("競技会区分") or row.get("competition") or "")),
        "条件": normalize_text(str(row.get("条件") or row.get("conditions") or "")),
    }
    return out


def dedupe_interactions(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for row in rows:
        norm = normalize_interaction_row(row)
        if not norm:
            continue
        key = pair_key(norm["成分A"], norm["成分B"])
        if key not in merged:
            merged[key] = norm
            continue
        existing = merged[key]
        level_rank = {"高": 3, "中": 2, "低": 1}
        if level_rank.get(norm["相互作用レベル"], 0) > level_rank.get(existing["相互作用レベル"], 0):
            existing["相互作用レベル"] = norm["相互作用レベル"]
        if len(norm.get("説明", "")) > len(existing.get("説明", "")):
            existing["説明"] = norm["説明"]
    return list(merged.values())


def dedupe_side_effects(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for row in rows:
        norm = normalize_side_effect_row(row)
        if not norm:
            continue
        key = normalize_text(norm["成分名"]).lower()
        if key not in merged:
            merged[key] = norm
            continue
        existing = merged[key]
        level_rank = {"高": 3, "中": 2, "低": 1}
        if level_rank.get(norm["副作用レベル"], 0) > level_rank.get(existing["副作用レベル"], 0):
            existing["副作用レベル"] = norm["副作用レベル"]
        for field in ("副作用症状", "禁忌条件"):
            if len(norm.get(field, "")) > len(existing.get(field, "")):
                existing[field] = norm[field]
    return list(merged.values())
