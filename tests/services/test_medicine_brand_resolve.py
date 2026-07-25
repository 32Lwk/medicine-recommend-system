"""ブランド通称 → 代表製品解決のテスト。"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src.core.medicine_data import CSV_PATH
from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query
from src.dialogue.routing.context_signals import extract_drug_entities
from src.services.medicine_brand_resolve import (
    BRAND_RESOLVE_RULES,
    MEDICINE_BRAND_HINTS,
    _brand_prefix_match,
    iter_brand_resolve_rules,
    resolve_brand_hint_product,
)


@pytest.fixture(scope="module")
def otc_df():
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV not available")
    return pd.read_csv(CSV_PATH, encoding="utf-8")


def test_registry_covers_all_brand_hints():
    registered = {h for rule in BRAND_RESOLVE_RULES for h in rule.hints}
    assert set(MEDICINE_BRAND_HINTS) == registered


def test_ib_does_not_match_keiboku():
    assert not _brand_prefix_match("イブ", "ケイブク（顆粒）")
    assert _brand_prefix_match("イブ", "イブ")
    assert _brand_prefix_match("イブ", "イブＡ錠")


def test_resolve_ib_to_ibuprofen_product(otc_df):
    med = resolve_brand_hint_product("イブ", otc_df)
    assert med is not None
    assert med["product_name"] == "イブ"
    assert "イブプロフェン" in str(med["ingredients"])


def test_advil_synonym_resolves_to_ib(otc_df):
    med = resolve_brand_hint_product("アドビル", otc_df)
    assert med is not None
    assert med["product_name"] == "イブ"


def test_resolve_loxonin_prefers_flagship(otc_df):
    med = resolve_brand_hint_product("ロキソニン", otc_df)
    assert med is not None
    assert med["product_name"] == "ロキソニンＳ"
    assert "ロキソプロフェン" in str(med["ingredients"])


def test_pl_resolves_to_pylon_pl(otc_df):
    med = resolve_brand_hint_product("PL", otc_df)
    assert med is not None
    assert "パイロンＰＬ" in med["product_name"]


def test_pabron_prefers_gold_tablet(otc_df):
    med = resolve_brand_hint_product("パブロン", otc_df)
    assert med is not None
    assert "パブロンゴールド" in med["product_name"]


def test_all_registered_hints_resolve(otc_df):
    for rule in iter_brand_resolve_rules():
        for hint in rule.hints:
            med = resolve_brand_hint_product(hint, otc_df)
            assert med is not None, f"hint={hint!r} rule={rule.hints}"


def test_comparison_query_detects_both_brands(otc_df):
    msg = "ロキソニンとイブの違いって何？"
    hits = detect_medicine_name_in_query(msg, otc_df)
    names = [h["product_name"] for h in hits]
    assert any("ロキソニン" in n for n in names)
    assert any(n == "イブ" or n.startswith("イブ") for n in names)
    assert not any("ケイブク" in n for n in names)
    assert len(hits) >= 2


def test_extract_drug_entities_includes_advil_via_registry():
    assert "アドビル" in extract_drug_entities("アドビルとバファリンの違い")
