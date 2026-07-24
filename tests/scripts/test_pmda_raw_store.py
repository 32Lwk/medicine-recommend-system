"""PMDA raw HTML 永続化のテスト。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.raw_store import (  # noqa: E402
    RAW_DIR,
    has_raw,
    load_raw,
    raw_file_path,
    save_ingredient_raw,
)


def test_save_and_load_raw(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.pmda.raw_store.RAW_DIR", tmp_path)
    monkeypatch.setattr("scripts.pmda.raw_store.RAW_INDEX", tmp_path / "index.json")

    path = save_ingredient_raw(
        "テスト成分",
        detail_html="<html>detail</html>",
        detail_fname="abc123",
        section10="10.2併用注意",
        section11="11.副作用",
    )
    assert path.is_file()
    assert has_raw("テスト成分")
    data = load_raw("テスト成分")
    assert data
    assert data["ingredient"] == "テスト成分"
    assert data["detail_html"] == "<html>detail</html>"
    assert data["section10_text"] == "10.2併用注意"


def test_raw_file_path_stable():
    p1 = raw_file_path("アスピリン")
    p2 = raw_file_path("アスピリン")
    assert p1 == p2
    assert p1.suffix == ".json"
