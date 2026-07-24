"""既存 side_effects + OTC 成分 alias から staging を拡張。"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from scripts.pmda.common import SIDE_EFFECTS_CSV, extract_otc_ingredients, read_csv_rows
from scripts.pmda.normalize import dedupe_side_effects, normalize_side_effect_row


def _ingredient_aliases(name: str, otc_ingredients: List[str]) -> List[str]:
    base = name.strip()
    if not base:
        return []
    aliases: Set[str] = {base}
    for ing in otc_ingredients:
        if base in ing or ing in base:
            aliases.add(ing)
        stem = re.sub(r"(ナトリウム|塩酸塩|水和物|マレイン酸塩|エキス|末)$", "", ing)
        if stem and (base in stem or stem in base):
            aliases.add(ing)
    return sorted(aliases)


def expand_side_effects_from_catalog() -> List[Dict[str, str]]:
    existing = read_csv_rows(SIDE_EFFECTS_CSV)
    otc_ingredients = extract_otc_ingredients()
    rows: List[Dict[str, str]] = []

    for row in existing:
        norm = normalize_side_effect_row(row)
        if not norm:
            continue
        rows.append(norm)
        for alias in _ingredient_aliases(norm["成分名"], otc_ingredients):
            if alias == norm["成分名"]:
                continue
            expanded = dict(norm)
            expanded["成分名"] = alias
            expanded["出典"] = norm.get("出典") or "PMDA-derived catalog expansion"
            rows.append(expanded)

    # OTC 主要成分で既存に無いものにテンプレート副作用行を追加
    seen = {normalize_side_effect_row(r)["成分名"].lower() for r in rows if normalize_side_effect_row(r)}
    stems = sorted(
        {
            re.sub(r"(ナトリウム|塩酸塩|水和物|マレイン酸塩|エキス|末)$", "", x)
            for x in otc_ingredients
            if len(x) >= 4
        }
    )[:180]
    for stem in stems:
        if stem.lower() in seen:
            continue
        rows.append(
            {
                "成分名": stem,
                "副作用レベル": "中",
                "副作用症状": "添付文書の副作用項参照（PMDA 市販薬成分）",
                "禁忌条件": "",
                "出典": "PMDA catalog ingredient expansion (review recommended)",
            }
        )
        seen.add(stem.lower())

    return dedupe_side_effects(rows)
