"""Triage cache TTL / LRU"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.services import llm_triage as lt


@pytest.fixture(autouse=True)
def _clear_legacy_triage_cache():
    lt._triage_cache.clear()
    yield
    lt._triage_cache.clear()


def test_triage_cache_entry_eviction():
    lt._triage_cache.clear()
    old = datetime.now() - timedelta(hours=25)
    lt._triage_cache["old:key"] = lt._TriageCacheEntry(created_at=old, result={"category": "Other"})
    lt._purge_triage_cache()
    assert "old:key" not in lt._triage_cache


def test_llm_triage_cache_hit_skips_api():
    from src.services.triage_cache import build_cache_key

    text = f"テスト頭痛キャッシュ専用_{uuid.uuid4().hex}"
    cache_key = build_cache_key(text)
    lt._triage_cache[cache_key] = lt._TriageCacheEntry(
        created_at=datetime.now(),
        result={"category": "Physical", "confidence": 0.9},
    )
    api_calls = []

    def _forbid_api(*_args, **_kwargs):
        api_calls.append(1)
        raise AssertionError("no api")

    with patch("src.services.budget_guard.check_llm_allowed", return_value=(True, None)):
        with patch("src.services.llm_triage.detect_illegal_or_controlled_drug", return_value=None):
            with patch("src.core.llm_client.chat_completion_create", side_effect=_forbid_api):
                r = lt.llm_triage(text, MagicMock(), use_cache=True)
    assert not api_calls
    assert r["category"] == "Physical"
