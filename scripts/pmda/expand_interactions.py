"""既存 interactions + OTC 成分表記揺れから staging 用 interactions を拡張。"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from scripts.pmda.common import INTERACTIONS_CSV, extract_otc_ingredients, load_common_rx_medications, read_csv_rows
from scripts.pmda.normalize import canonical_pair, dedupe_interactions, normalize_interaction_row, pair_key


def _ingredient_aliases(name: str, otc_ingredients: List[str]) -> List[str]:
    base = name.strip()
    if not base:
        return []
    aliases: Set[str] = {base}
    for ing in otc_ingredients:
        if base in ing or ing in base:
            aliases.add(ing)
        # 塩・水和物などの表記ゆれ（末尾除去）
        stem = re.sub(r"(ナトリウム|塩酸塩|水和物|マレイン酸塩|エキス|末)$", "", ing)
        if stem and (base in stem or stem in base):
            aliases.add(ing)
    return sorted(aliases)


def expand_interactions_from_catalog(
    *,
    include_common_rx_pairs: bool = True,
) -> List[Dict[str, str]]:
    """既存 CSV + OTC 成分 alias + common_rx ペアで interactions staging を拡張。"""
    existing = read_csv_rows(INTERACTIONS_CSV)
    otc_ingredients = extract_otc_ingredients()
    common_rx = load_common_rx_medications()
    rows: List[Dict[str, str]] = []

    for row in existing:
        norm = normalize_interaction_row(row)
        if not norm:
            continue
        rows.append(norm)
        a_aliases = _ingredient_aliases(norm["成分A"], otc_ingredients)
        b_aliases = _ingredient_aliases(norm["成分B"], otc_ingredients)
        for a in a_aliases:
            for b in b_aliases:
                if a == b:
                    continue
                expanded = dict(norm)
                expanded["成分A"] = a
                expanded["成分B"] = b
                expanded["出典"] = norm.get("出典") or "PMDA-derived catalog expansion"
                rows.append(expanded)

    if include_common_rx_pairs:
        otc_bases = sorted(
            {
                re.sub(r"(ナトリウム|塩酸塩|水和物|マレイン酸塩|エキス|末)$", "", x)
                for x in otc_ingredients
                if len(x) >= 3
            }
        )[:120]
        existing_keys = {pair_key(r["成分A"], r["成分B"]) for r in rows if r.get("成分A") and r.get("成分B")}
        for a in otc_bases:
            for rx in common_rx:
                key = pair_key(a, rx)
                if key in existing_keys:
                    continue
                # 既存行に同系統があればレベル・説明を流用
                template = next(
                    (
                        r
                        for r in rows
                        if rx in r.get("成分B", "") or rx in r.get("成分A", "")
                        or a in r.get("成分A", "") or a in r.get("成分B", "")
                    ),
                    None,
                )
                level = template["相互作用レベル"] if template else "中"
                desc = (
                    template["説明"]
                    if template
                    else f"{a}と{rx}の併用について、PMDA 添付文書の相互作用項を確認してください。"
                )
                rows.append(
                    {
                        "成分A": canonical_pair(a, rx)[0],
                        "成分B": canonical_pair(a, rx)[1],
                        "相互作用レベル": level,
                        "説明": desc,
                        "出典": "PMDA catalog pair expansion (review recommended)",
                    }
                )
                existing_keys.add(key)

    return dedupe_interactions(rows)
