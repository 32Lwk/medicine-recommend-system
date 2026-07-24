"""build_medicine_kb_documents metadata 規約テスト。"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.build_medicine_kb_documents import (
    _stringify_metadata_values,
    write_doc_pair,
)


def test_stringify_metadata_converts_booleans():
    meta = _stringify_metadata_values(
        {"has_age_restriction": True, "has_doping_info": False, "domain": "medicine"}
    )
    assert meta == {
        "has_age_restriction": "true",
        "has_doping_info": "false",
        "domain": "medicine",
    }


def test_write_doc_pair_metadata_has_no_json_booleans():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "products" / "sample"
        write_doc_pair(
            base,
            "# Sample\n",
            {
                "domain": "medicine",
                "doc_type": "product",
                "has_age_restriction": True,
                "has_doping_info": False,
            },
        )
        meta_path = Path(f"{base}.md.metadata.json")
        raw = meta_path.read_text(encoding="utf-8")
        assert "true" in raw
        assert "false" in raw
        assert ": true" not in raw
        assert ": false" not in raw
        parsed = json.loads(raw)
        attrs = parsed["metadataAttributes"]
        assert all(isinstance(v, str) for v in attrs.values())
