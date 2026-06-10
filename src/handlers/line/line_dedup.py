"""LINE webhookEventId のメモリ内去重（TTL）。"""
from __future__ import annotations

import time

_TTL_SEC = 120.0
_seen: dict[str, float] = {}


def _purge_expired(now: float) -> None:
    expired = [k for k, ts in _seen.items() if now - ts > _TTL_SEC]
    for key in expired:
        del _seen[key]


def mark_webhook_event_seen(event_id: str | None) -> bool:
    """
    イベント ID を記録する。

    Returns:
        True  if duplicate (already seen within TTL)
        False if newly recorded
    """
    if not event_id:
        return False
    now = time.time()
    _purge_expired(now)
    if event_id in _seen:
        return True
    _seen[event_id] = now
    return False


def reset_dedup_cache_for_tests() -> None:
    """テスト用にキャッシュをクリア。"""
    _seen.clear()
