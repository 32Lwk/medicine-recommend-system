"""Triage cache TTL / LRU"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.services import llm_triage as lt


def test_triage_cache_entry_eviction():
    lt._triage_cache.clear()
    old = datetime.now() - timedelta(hours=25)
    lt._triage_cache["old:key"] = lt._TriageCacheEntry(created_at=old, result={"category": "Other"})
    lt._purge_triage_cache()
    assert "old:key" not in lt._triage_cache


def test_llm_triage_cache_hit_skips_api():
    lt._triage_cache.clear()
    text = "テスト頭痛"
    lt._triage_cache[text.strip()] = lt._TriageCacheEntry(
        created_at=datetime.now(),
        result={"category": "Physical", "confidence": 0.9},
    )
    with patch("src.core.llm_client.chat_completion_create", side_effect=AssertionError("no api")):
        r = lt.llm_triage(text, MagicMock(), use_cache=True)
    assert r["category"] == "Physical"
