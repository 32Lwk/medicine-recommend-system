"""staging 正規化データを data/*.csv に merge。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from scripts.pmda.common import (
    INTERACTIONS_CSV,
    OTC_CSV,
    SIDE_EFFECTS_CSV,
    INGREDIENT_DICT_JSON,
    product_key,
    read_csv_rows,
    update_manifest,
    write_csv_rows,
    load_json,
    save_json,
    normalize_text,
)
from scripts.pmda.http_client import PMDA_LIVE_SOURCE_LABELS  # noqa: E402
from scripts.pmda.normalize import (
    dedupe_interactions,
    dedupe_side_effects,
    normalize_interaction_row,
    normalize_side_effect_row,
    normalize_otc_product_row,
    pair_key,
)


INTERACTION_FIELDS = ["成分A", "成分B", "相互作用レベル", "説明", "出典", "pmda_updated_at", "interaction_id"]
SIDE_EFFECT_FIELDS = ["成分名", "副作用レベル", "副作用症状", "禁忌条件", "出典"]
OTC_FIELDS = [
    "製品名",
    "メーカー名",
    "分類",
    "医薬品の種類",
    "効能効果",
    "用法用量",
    "年齢制限",
    "成分",
    "禁止物質あり",
    "競技会区分",
    "条件",
    "pmda_薬効分類",
    "pmda_リスク区分",
]


def _existing_interaction_keys() -> Set[str]:
    keys: Set[str] = set()
    for row in read_csv_rows(INTERACTIONS_CSV):
        norm = normalize_interaction_row(row)
        if norm:
            keys.add(pair_key(norm["成分A"], norm["成分B"]))
    return keys


def merge_interactions(
    rows: List[Dict[str, Any]],
    *,
    preserve_existing: bool = True,
    live_replace: bool = False,
) -> Dict[str, Any]:
    existing_rows = read_csv_rows(INTERACTIONS_CSV) if preserve_existing else []
    existing_norm = [
        normalize_interaction_row(r) for r in existing_rows if normalize_interaction_row(r)
    ]
    incoming = [
        normalize_interaction_row(r) for r in rows if normalize_interaction_row(r)
    ]
    if live_replace:
        incoming_pmda = [r for r in incoming if r.get("出典") in PMDA_LIVE_SOURCE_LABELS]
        kept = [r for r in existing_norm if r.get("出典") not in PMDA_LIVE_SOURCE_LABELS]
        merged = dedupe_interactions(kept + incoming_pmda)
    else:
        merged = dedupe_interactions(existing_norm + incoming)

    before = len(existing_rows)
    count = write_csv_rows(INTERACTIONS_CSV, INTERACTION_FIELDS, merged)
    update_manifest(medicine_interactions={"row_count": count, "pair_policy": "otc_plus_common_rx"})
    return {"before": before, "after": count, "added": max(0, count - before), "live_replace": live_replace}


def merge_side_effects(
    rows: List[Dict[str, Any]],
    *,
    preserve_existing: bool = True,
    live_replace: bool = False,
) -> Dict[str, Any]:
    existing_rows = read_csv_rows(SIDE_EFFECTS_CSV) if preserve_existing else []
    existing_norm = [
        normalize_side_effect_row(r) for r in existing_rows if normalize_side_effect_row(r)
    ]
    incoming = [normalize_side_effect_row(r) for r in rows if normalize_side_effect_row(r)]
    if live_replace:
        incoming_pmda = [r for r in incoming if r.get("出典") in PMDA_LIVE_SOURCE_LABELS]
        kept = [r for r in existing_norm if r.get("出典") not in PMDA_LIVE_SOURCE_LABELS]
        merged = dedupe_side_effects(kept + incoming_pmda)
    else:
        merged = dedupe_side_effects(existing_norm + incoming)

    before = len(existing_rows)
    count = write_csv_rows(SIDE_EFFECTS_CSV, SIDE_EFFECT_FIELDS, merged)
    update_manifest(medicine_side_effects={"row_count": count})
    _extend_ingredient_dictionary([r["成分名"] for r in merged])
    return {"before": before, "after": count, "added": max(0, count - before), "live_replace": live_replace}


def merge_otc_products(
    rows: List[Dict[str, Any]],
    *,
    pmda_priority: bool = True,
) -> Dict[str, Any]:
    existing = read_csv_rows(OTC_CSV)
    staging_by_key: Dict[str, Dict[str, str]] = {}
    for row in rows:
        norm = normalize_otc_product_row(row)
        if norm:
            staging_by_key[product_key(norm["製品名"], norm["メーカー名"])] = norm

    added = updated = 0
    merged_rows: List[Dict[str, str]] = []
    seen_keys: Set[str] = set()

    for row in existing:
        norm = normalize_otc_product_row(row)
        if not norm:
            merged_rows.append(row)
            continue
        key = product_key(norm["製品名"], norm["メーカー名"])
        seen_keys.add(key)
        if key in staging_by_key and pmda_priority:
            patch = staging_by_key[key]
            changed = False
            # 分類・医薬品の種類は既存タクソノミを保持。
            # PMDA 薬効分類/リスク区分は専用カラムへ保存する。
            for field in ("効能効果", "用法用量", "年齢制限", "成分", "pmda_薬効分類", "pmda_リスク区分"):
                if patch.get(field) and patch.get(field) != norm.get(field):
                    norm[field] = patch[field]
                    changed = True
            if changed:
                updated += 1
        merged_rows.append(norm)

    for key, norm in staging_by_key.items():
        if key not in seen_keys:
            merged_rows.append(norm)
            added += 1

    count = write_csv_rows(OTC_CSV, OTC_FIELDS, merged_rows)
    update_manifest(otc_medicine_data={"row_count": count, "source": "PMDA OTC Search"})
    return {"before": len(existing), "after": count, "added": added, "updated": updated}


def _extend_ingredient_dictionary(ingredients: List[str]) -> None:
    data = load_json(INGREDIENT_DICT_JSON, {})
    if not isinstance(data, dict):
        data = {}
    changed = False
    for name in ingredients:
        key = normalize_text(name)
        if not key or key in data:
            continue
        data[key] = {
            "canonical_name": key,
            "synonyms": [key],
            "source": "pmda_import",
        }
        changed = True
    if changed:
        save_json(INGREDIENT_DICT_JSON, data)
