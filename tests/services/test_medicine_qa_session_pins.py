"""セッション内ブランドピン留めのテスト。"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src.core.medicine_data import CSV_PATH
from src.services.medicine_brand_resolve import resolve_brand_hint_product, resolve_brand_hints_in_query
from src.services.medicine_qa_session_pins import (
    SESSION_PIN_KEY,
    get_session_brand_pins,
    prefer_pinned_product,
    remember_resolved_brand_products,
    resolve_products_with_session_pins,
    write_session_brand_pins,
)


@pytest.fixture(scope="module")
def otc_df():
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV not available")
    return pd.read_csv(CSV_PATH, encoding="utf-8")


def test_pin_persists_bufferin_choice(otc_df):
    session: dict = {}
    first = resolve_brand_hint_product("バファリン", otc_df)
    assert first is not None
    remember_resolved_brand_products(
        session,
        user_message="ロキソニンとイブ、バファリンの違いって何？",
        products=[first],
        drug_hints=["バファリン"],
    )
    pins = get_session_brand_pins(session)
    assert "バファリン" in pins
    pinned_name = pins["バファリン"]["product_name"]

    # 同一セッションで再解決 → ピン優先
    again = prefer_pinned_product(
        "バファリン",
        user_message="バファリンとイブの違いは？",
        medicine_df=otc_df,
        session_pins=pins,
        freshly_resolved=resolve_brand_hint_product("バファリン", otc_df),
    )
    assert again is not None
    assert again["product_name"] == pinned_name


def test_explicit_product_overrides_pin(otc_df):
    session: dict = {}
    write_session_brand_pins(
        session,
        {"バファリン": {"product_name": "バファリンＡ", "ingredients": "アスピリン"}},
    )
    # ユーザーがプレミアムを明示 → ピンより優先
    med = prefer_pinned_product(
        "バファリン",
        user_message="バファリンプレミアムとロキソニンの違いは？",
        medicine_df=otc_df,
        session_pins=get_session_brand_pins(session),
        freshly_resolved=resolve_brand_hint_product("バファリン", otc_df),
    )
    assert med is not None
    assert "プレミアム" in med["product_name"] or "プレミアム" in str(med)


def test_resolve_with_session_pins_roundtrip(otc_df):
    session: dict = {}
    products = resolve_products_with_session_pins(
        "ロキソニンとイブの違いって何？",
        otc_df,
        session=session,
    )
    assert len(products) >= 2
    assert SESSION_PIN_KEY in session
    names1 = [p["product_name"] for p in products]

    products2 = resolve_brand_hints_in_query(
        "ロキソニンとイブどっちがいい？",
        otc_df,
        session=session,
    )
    names2 = [p["product_name"] for p in products2]
    # セッション内で同一ブランドは同一代表製品
    for brand_prefix in ("ロキソニン", "イブ"):
        n1 = next((n for n in names1 if n.startswith(brand_prefix)), None)
        n2 = next((n for n in names2 if n.startswith(brand_prefix)), None)
        if n1 and n2:
            assert n1 == n2
