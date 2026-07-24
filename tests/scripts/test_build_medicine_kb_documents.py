"""build_medicine_kb_documents.py — slug 衝突と metadata サイズ。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_medicine_kb_documents import (  # noqa: E402
    METADATA_MAX_BYTES,
    allocate_unique_slug,
    kb_product_slug,
    _truncate_metadata,
)


def test_kb_product_slug_stable():
    s1 = kb_product_slug("カロナールA", "第一三共")
    s2 = kb_product_slug("カロナールA", "第一三共")
    assert s1 == s2
    assert len(s1) >= 2


def test_allocate_unique_slug_collision_suffix():
    used = {}
    a = allocate_unique_slug("ロキソニン-第一三共", used)
    b = allocate_unique_slug("ロキソニン-第一三共", used)
    assert a != b
    assert b.endswith("-2")


def test_metadata_under_1kb():
    meta = {
        "domain": "medicine",
        "doc_type": "product",
        "product_name": "テスト" * 20,
        "manufacturer": "メーカー" * 5,
        "classification": "指定第2類",
    }
    trimmed = _truncate_metadata(meta)
    wrapped = {"metadataAttributes": trimmed}
    assert len(json.dumps(wrapped, ensure_ascii=False).encode("utf-8")) <= METADATA_MAX_BYTES
