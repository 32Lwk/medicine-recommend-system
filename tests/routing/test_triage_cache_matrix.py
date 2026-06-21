"""トリアージキャッシュ skip 行列"""
from __future__ import annotations

import os
from unittest.mock import patch

from src.services.triage_cache import (
    build_cache_key,
    get_cache_metrics,
    should_skip_cache_lookup,
    should_skip_cache_write,
)


def test_cache_key_is_sha256_hex():
    k1 = build_cache_key("頭痛", {"age": 30, "gender": "女性"})
    k2 = build_cache_key("頭痛", {"age": 30, "gender": "女性"})
    assert k1 == k2
    assert len(k1) == 64


def test_cache_key_differs_when_memory_digest_changes():
    k1 = build_cache_key("頭痛", history_digest="abc", memory_digest="")
    k2 = build_cache_key("頭痛", history_digest="abc", memory_digest="mem1")
    assert k1 != k2


def test_skip_emergency():
    assert (
        should_skip_cache_lookup(text="胸がとても痛いです", triage_result={"category": "Emergency"})
        == "emergency"
    )


def test_skip_min_chars():
    assert should_skip_cache_lookup(text="a") == "min_chars"


def test_skip_low_confidence_write():
    assert (
        should_skip_cache_write(
            text="頭がとても痛いです",
            result={"category": "Physical", "confidence": 0.2},
        )
        == "low_confidence"
    )


@patch.dict(os.environ, {"TRIAGE_CACHE_DISABLED": "1"}, clear=False)
def test_skip_disabled_flag():
    assert should_skip_cache_lookup(text="頭がとても痛いです") == "disabled_flag"
    assert get_cache_metrics()["hit"] >= 0
