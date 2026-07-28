"""セッション単位のチャット POST 重複実行防止（SSE ワーカーと JSON POST で共有）。"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, Optional

_IN_FLIGHT_TTL_SEC = 300.0
_lock = threading.Lock()
_in_flight: Dict[str, str] = {}  # sid -> job token
_job_token = threading.local()


def _redis_inflight_key(sid: str) -> str:
    return f"chat:inflight:{sid}"


def _redis_configured() -> bool:
    try:
        from config.aws_features import get_redis_url

        return bool((get_redis_url() or "").strip())
    except Exception:
        return False


def _redis_try_acquire(sid: str, token: str) -> Optional[bool]:
    """True=取得, False=他 worker 占有, None=Redis 未設定（ローカルのみ）。"""
    if not _redis_configured():
        return None
    try:
        from src.services.redis_cache import cache_set_nx

        return cache_set_nx(_redis_inflight_key(sid), token, ttl_sec=int(_IN_FLIGHT_TTL_SEC))
    except Exception:
        return None


def _redis_release(sid: str, token: Optional[str] = None) -> None:
    if not _redis_configured():
        return
    try:
        from src.services.redis_cache import cache_delete, cache_get

        key = _redis_inflight_key(sid)
        if token is not None:
            current = cache_get(key)
            if current and current != token:
                return
        cache_delete(key)
    except Exception:
        pass


def _redis_get_token(sid: str) -> Optional[str]:
    if not _redis_configured():
        return None
    try:
        from src.services.redis_cache import cache_get

        return cache_get(_redis_inflight_key(sid))
    except Exception:
        return None


def _set_job_token(token: str) -> None:
    _job_token.value = token


def get_current_job_token() -> Optional[str]:
    return getattr(_job_token, "value", None)


def try_begin_chat_job(sid: Optional[str]) -> bool:
    """同一 sid の処理が進行中なら False。開始できたら True。"""
    if not sid:
        return True
    token = uuid.uuid4().hex
    with _lock:
        if sid in _in_flight:
            return False
        redis_result = _redis_try_acquire(sid, token)
        if redis_result is False:
            return False
        _in_flight[sid] = token
        _set_job_token(token)
        return True


def end_chat_job(sid: Optional[str]) -> None:
    if not sid:
        return
    token = get_current_job_token()
    with _lock:
        local_token = _in_flight.pop(sid, None)
    release_token = token or local_token
    _redis_release(sid, release_token)
    if getattr(_job_token, "value", None) == release_token:
        _job_token.value = None


def is_chat_job_in_flight(sid: Optional[str]) -> bool:
    """同一 sid のチャット処理が進行中か（ロックは取らない）。"""
    if not sid:
        return False
    redis_token = _redis_get_token(sid)
    if redis_token:
        return True
    with _lock:
        return sid in _in_flight


def get_chat_job_token(sid: Optional[str]) -> Optional[str]:
    """進行中ジョブの token（orphan persist の stale 判定用）。"""
    if not sid:
        return None
    redis_token = _redis_get_token(sid)
    if redis_token:
        return redis_token
    with _lock:
        return _in_flight.get(sid)


def should_orphan_persist(sid: Optional[str], orphan_token: Optional[str]) -> bool:
    """新しい chat job が開始済みなら orphan の DB 書込をスキップ。"""
    if not sid or not orphan_token:
        return True
    current = get_chat_job_token(sid)
    if current and current != orphan_token:
        return False
    return True
