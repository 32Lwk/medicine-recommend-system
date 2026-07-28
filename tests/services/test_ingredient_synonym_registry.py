"""Tests for ingredient_synonym_registry."""
from __future__ import annotations

from src.services.ingredient_synonym_registry import (
    alias_to_canonical,
    brand_hints_for_product,
    brand_query_shorthands,
    expand_query_with_aliases,
    lookup_synonyms_for_names,
)


def test_brand_query_shorthands_includes_loxoprofen():
    sh = brand_query_shorthands()
    assert "ロキソニン" in sh
    assert sh.get("ロキソ") == "ロキソニン"


def test_lookup_synonyms_for_ibuprofen_brand():
    blob = lookup_synonyms_for_names(["イブ", "イブプロフェン"])
    assert "イブ" in blob or "イブプロフェン" in blob


def test_expand_query_with_aliases_adds_canonical():
    q = expand_query_with_aliases("ロキソ飲んだら眠い")
    assert "ロキソプロフェン" in q or "ロキソニン" in q


def test_brand_hints_for_loxoprofen_product():
    hints = brand_hints_for_product("ロキソニンＳ")
    assert "ロキソニン" in hints


def test_alias_to_canonical_not_empty():
    m = alias_to_canonical()
    assert len(m) > 100
    assert m.get("イブ") or m.get("イブプロフェン")
