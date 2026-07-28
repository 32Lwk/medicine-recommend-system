"""redis_cache.py — no-op when REDIS_URL unset"""
from src.services import redis_cache


def test_cache_noop_without_redis(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    redis_cache._client = None
    redis_cache._client_failed = False
    assert redis_cache.cache_get("k") is None
    redis_cache.cache_set("k", "v")
    assert redis_cache.cache_get("k") is None
    assert redis_cache.cache_set_nx("nx-key", "1", ttl_sec=60) is False
