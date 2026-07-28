"""セッション単位のチャット POST 重複実行防止（SSE ワーカーと JSON POST で共有）。"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_IN_FLIGHT_TTL_SEC = 300.0
_lock = threading.Lock()
_in_flight: Dict[str, str] = {}  # sid -> job token
_in_flight_started: Dict[str, float] = {}  # sid -> monotonic started at
_sid_stream_setup_locks: Dict[str, threading.Lock] = {}
_job_token = threading.local()


def stream_setup_lock(sid: str) -> threading.Lock:
    with _lock:
        lk = _sid_stream_setup_locks.get(sid)
        if lk is None:
            lk = threading.Lock()
            _sid_stream_setup_locks[sid] = lk
        return lk


def _purge_stale_inflight_unlocked(now: Optional[float] = None) -> None:
    ts = now if now is not None else time.monotonic()
    stale = [
        sid
        for sid, started in _in_flight_started.items()
        if ts - started > _IN_FLIGHT_TTL_SEC
    ]
    for sid in stale:
        _in_flight.pop(sid, None)
        _in_flight_started.pop(sid, None)


def force_clear_stale_chat_job(sid: Optional[str]) -> bool:
    """アクティブ sink / ワーカーが無いのに inflight だけ残った場合に解放。"""
    if not sid:
        return False
    from src.services.sse_emit import get_active_session_sink, peek_stream_result

    if get_active_session_sink(sid):
        return False
    if peek_stream_result(sid):
        return False
    with _lock:
        if sid not in _in_flight:
            return False
        _in_flight.pop(sid, None)
        _in_flight_started.pop(sid, None)
    _redis_release(sid)
    return True


def _redis_inflight_key(sid: str) -> str:
    return f"chat:inflight:{sid}"


def _redis_configured() -> bool:
    try:
        from config.aws_features import get_redis_url

        return bool((get_redis_url() or "").strip())
    except Exception:
        return False


def _redis_client_available() -> bool:
    if not _redis_configured():
        return False
    try:
        from src.services.redis_cache import _redis_client

        return _redis_client() is not None
    except Exception:
        return False


def _redis_try_acquire(sid: str, token: str) -> Optional[bool]:
    """True=取得, False=他 worker 占有, None=Redis 未使用（ローカルのみ）。"""
    if not _redis_client_available():
        return None
    try:
        from src.services.redis_cache import cache_set_nx

        return cache_set_nx(_redis_inflight_key(sid), token, ttl_sec=int(_IN_FLIGHT_TTL_SEC))
    except Exception:
        return None


def _redis_release(sid: str, token: Optional[str] = None) -> None:
    if not _redis_client_available():
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
    if not _redis_client_available():
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


def bind_job_token(token: Optional[str]) -> None:
    """ワーカースレッドへ stream 側で確保した job token を引き渡す。"""
    if token:
        _set_job_token(token)


def reserve_chat_job(sid: Optional[str]) -> Optional[str]:
    """SSE ストリーム開始時に同期的に inflight を確保。token または None（占有中）。"""
    if not sid:
        return ""
    token = _begin_chat_job_token(sid)
    if token is None:
        return None
    return token


def try_begin_chat_job(sid: Optional[str]) -> bool:
    """同一 sid の処理が進行中なら False。開始できたら True。"""
    if not sid:
        return True
    return _begin_chat_job_token(sid) is not None


def _begin_chat_job_token(sid: str) -> Optional[str]:
    """inflight 確保。成功時 token、占有時 None。"""
    token = uuid.uuid4().hex
    now = time.monotonic()
    with _lock:
        _purge_stale_inflight_unlocked(now)
        if sid in _in_flight:
            logger.warning("try_begin_chat_job blocked sid=%s inflight=%s", sid, list(_in_flight.keys()))
            return None
        redis_result = _redis_try_acquire(sid, token)
        if redis_result is False:
            return None
        _in_flight[sid] = token
        _in_flight_started[sid] = now
    _set_job_token(token)
    return token


def end_chat_job(sid: Optional[str]) -> None:
    if not sid:
        return
    token = get_current_job_token()
    with _lock:
        local_token = _in_flight.pop(sid, None)
        _in_flight_started.pop(sid, None)
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
