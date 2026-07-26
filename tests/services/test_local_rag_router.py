"""local_rag_router.py — interaction / category routing unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "medicine"


pytestmark = pytest.mark.skipif(
    not BUILD.is_dir(),
    reason="build/medicine corpus not present",
)


INTERACTION_CASES = [
    (
        "ロキソプロフェンとワーファリンを一緒に飲んでも大丈夫？",
        ["ロキソニン"],
        "interactions/ロキソプロフェン-ワーファリン.md",
    ),
    (
        "イブプロフェンとアスピリンの併用は？",
        [],
        "interactions/アスピリン-イブプロフェン.md",
    ),
    (
        "アセトアミノフェンをお酒と一緒に飲むと？",
        [],
        "interactions/アセトアミノフェン-アルコール.md",
    ),
    (
        "デキストロメトルファンと SSRI の併用リスクは？",
        [],
        "interactions/ssri-デキストロメトルファン.md",
    ),
    (
        "カフェインとエフェドリンを同時に取ると？",
        [],
        "interactions/エフェドリン-カフェイン.md",
    ),
]


@pytest.mark.parametrize("query,meds,expected_suffix", INTERACTION_CASES)
def test_route_interaction_fixture(query, meds, expected_suffix):
    from src.services.local_rag_router import route_medicine_doc

    recommended = [{"product_name": m} for m in meds]
    result = route_medicine_doc(query, recommended_medicines=recommended, category="interaction")
    assert result is not None, query
    path, virtual_uri, score = result
    assert expected_suffix.replace("\\", "/") in path.as_posix()
    assert "medicine/" in virtual_uri
    assert score >= 0.85


def test_infer_medicine_category_interaction():
    from src.services.local_rag_router import infer_medicine_category

    assert infer_medicine_category("併用して大丈夫？") == "interaction"


def test_resolve_product_by_metadata_name():
    from src.services.local_rag_router import _resolve_product_by_name

    path = _resolve_product_by_name("カロナールA")
    if path is None:
        pytest.skip("カロナールA product doc not in build/medicine")
    assert path.name.endswith(".md")
