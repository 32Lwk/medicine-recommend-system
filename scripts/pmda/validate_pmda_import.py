"""PMDA staging データの検証。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from scripts.pmda.common import STAGING_INTERACTIONS, STAGING_OTC, STAGING_SIDE_EFFECTS, load_json
from scripts.pmda.normalize import (
    dedupe_interactions,
    dedupe_side_effects,
    normalize_interaction_row,
    normalize_side_effect_row,
    normalize_otc_product_row,
    pair_key,
)


def validate_interactions(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, str]]]:
    errors: List[str] = []
    normalized: List[Dict[str, str]] = []
    seen = set()
    for i, row in enumerate(rows):
        norm = normalize_interaction_row(row)
        if not norm:
            errors.append(f"interactions[{i}]: missing 成分A/成分B")
            continue
        key = pair_key(norm["成分A"], norm["成分B"])
        if key in seen:
            errors.append(f"interactions[{i}]: duplicate pair {norm['成分A']} x {norm['成分B']}")
        seen.add(key)
        normalized.append(norm)
    return errors, dedupe_interactions(normalized)


def validate_side_effects(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, str]]]:
    errors: List[str] = []
    normalized: List[Dict[str, str]] = []
    for i, row in enumerate(rows):
        norm = normalize_side_effect_row(row)
        if not norm:
            errors.append(f"side_effects[{i}]: missing 成分名")
            continue
        normalized.append(norm)
    return errors, dedupe_side_effects(normalized)


def validate_otc_products(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, str]]]:
    errors: List[str] = []
    normalized: List[Dict[str, str]] = []
    for i, row in enumerate(rows):
        norm = normalize_otc_product_row(row)
        if not norm:
            errors.append(f"otc[{i}]: missing 製品名")
            continue
        normalized.append(norm)
    return errors, normalized


def _load_staging_list(path) -> List[Dict[str, Any]]:
    data = load_json(path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def validate_all_staging() -> Dict[str, Any]:
    ix_errors, ix_rows = validate_interactions(_load_staging_list(STAGING_INTERACTIONS))
    se_errors, se_rows = validate_side_effects(_load_staging_list(STAGING_SIDE_EFFECTS))
    otc_errors, otc_rows = validate_otc_products(_load_staging_list(STAGING_OTC))
    return {
        "ok": not (ix_errors or se_errors or otc_errors),
        "interactions": {"errors": ix_errors, "count": len(ix_rows)},
        "side_effects": {"errors": se_errors, "count": len(se_rows)},
        "otc_products": {"errors": otc_errors, "count": len(otc_rows)},
        "normalized": {
            "interactions": ix_rows,
            "side_effects": se_rows,
            "otc_products": otc_rows,
        },
    }
