"""副作用 Q&A セクション生成（medicine_qa / side_effect_qa 共通）。"""
from __future__ import annotations

import os
from typing import Any

from src.core.medicine_data import CSV_PATH
from src.core.scoring_utils import load_side_effects_data, normalize_medicine_name_to_hankaku
from src.services.medicine_side_effect_routing import mentions_drowsiness_side_effect
from src.services.side_effect_display import (
    build_concise_side_effect_answer,
    build_drowsiness_answer,
    build_side_effect_cards_html,
)


def _ingredients_for_products(products: list[dict[str, Any]]) -> list[str]:
    ingredients: list[str] = []
    for p in products:
        raw = str(p.get("ingredients") or "")
        for part in raw.replace("\n", ",").split(","):
            part = part.strip()
            if part and part not in ingredients:
                ingredients.append(part)
    return ingredients


def side_effect_rows_for_ingredients(ingredients: list[str]) -> list[dict[str, Any]]:
    df = load_side_effects_data()
    if df is None or df.empty or not ingredients:
        return []
    rows: list[dict[str, Any]] = []
    for ing in ingredients:
        norm = normalize_medicine_name_to_hankaku(ing).lower()
        for _, row in df.iterrows():
            cell = normalize_medicine_name_to_hankaku(str(row.get("成分名") or "")).lower()
            if norm and (norm in cell or cell in norm):
                rows.append(row.to_dict())
                break
    return rows


def build_side_effect_section(
    user_message: str,
    products: list[dict[str, Any]],
    *,
    product_name: str = "",
) -> dict[str, Any]:
    """CSV/PMDA ベースの副作用セクション（answer 省略可）。"""
    pname = product_name or (
        str(products[0].get("product_name") or "") if products else ""
    )
    ingredients = _ingredients_for_products(products) if products else []
    side_rows = side_effect_rows_for_ingredients(ingredients)
    is_drowsiness = mentions_drowsiness_side_effect(user_message)

    side_effect_html = ""
    if side_rows:
        side_effect_html = build_side_effect_cards_html(
            side_rows,
            reference_only=is_drowsiness,
        )

    if is_drowsiness:
        answer = build_drowsiness_answer(pname, side_rows)
    else:
        answer = build_concise_side_effect_answer(pname, side_rows)

    side_text = ""
    if side_rows and not side_effect_html:
        parts = [
            str(r.get("副作用名") or r.get("症状") or "").strip()
            for r in side_rows[:5]
        ]
        side_text = "、".join(p for p in parts if p)

    return {
        "answer": answer,
        "side_effects": side_text,
        "side_effect_html": side_effect_html,
        "side_effect_reference": is_drowsiness,
        "side_rows": side_rows,
    }


def find_products_for_side_effect(query: str) -> list[dict[str, Any]]:
    from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query

    try:
        import pandas as pd

        if not os.path.exists(CSV_PATH):
            return []
        df = pd.read_csv(CSV_PATH, encoding="utf-8")
        return detect_medicine_name_in_query(query, df)
    except Exception:
        return []
