"""meta_triage リクエストスコープキャッシュのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.meta_triage import classify_meta_concierge_intent
from src.services.request_scope_cache import clear_request_scope_cache


def test_classify_meta_concierge_intent_dedupes_within_request():
    clear_request_scope_cache()
    client = MagicMock()
    with patch("src.services.meta_triage._classify_meta_concierge_intent_impl") as impl:
        impl.return_value = "greeting"
        r1 = classify_meta_concierge_intent("こんにちは", client)
        r2 = classify_meta_concierge_intent("こんにちは", client)
        assert r1 == "greeting"
        assert r2 == "greeting"
        assert impl.call_count == 1
