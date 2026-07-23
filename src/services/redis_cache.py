"""Redis read-through cache（REDIS_URL 未設定時は no-op）。"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client = None
_client_failed = False


def _redis_client():
    global _client, _client_failed
    if _client_failed:
        return None
    if _client is not None:
        return _client
    from config.aws_features import get_redis_url

    url = get_redis_url()
    if not url:
        return None
    try:
        import redis

        _client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _client.ping()
        return _client
    except Exception as exc:
        logger.warning("Redis unavailable, cache disabled: %s", exc)
        _client_failed = True
        return None


def cache_get(key: str) -> Optional[str]:
    client = _redis_client()
    if not client:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        logger.debug("Redis GET failed for %s: %s", key, exc)
        return None


def cache_set(key: str, value: str, *, ttl_sec: int = 600) -> None:
    client = _redis_client()
    if not client:
        return
    try:
        client.setex(key, ttl_sec, value)
    except Exception as exc:
        logger.debug("Redis SET failed for %s: %s", key, exc)


def cache_get_json(key: str) -> Any:
    raw = cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set_json(key: str, value: Any, *, ttl_sec: int = 600) -> None:
    cache_set(key, json.dumps(value, ensure_ascii=False), ttl_sec=ttl_sec)
