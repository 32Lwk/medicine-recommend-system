"""セッション単位のチャット POST 重複実行防止（SSE ワーカーと JSON POST で共有）。"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional

_IN_FLIGHT_TTL_SEC = 300.0
_lock = threading.Lock()
_in_flight: Dict[str, float] = {}


def _prune_stale(now: float) -> None:
    stale = [k for k, t in _in_flight.items() if now - t > _IN_FLIGHT_TTL_SEC]
    for k in stale:
        _in_flight.pop(k, None)


def try_begin_chat_job(sid: Optional[str]) -> bool:
    """同一 sid の処理が進行中なら False。開始できたら True。"""
    if not sid:
        return True
    now = time.monotonic()
    with _lock:
        _prune_stale(now)
        if sid in _in_flight:
            return False
        _in_flight[sid] = now
        return True


def end_chat_job(sid: Optional[str]) -> None:
    if not sid:
        return
    with _lock:
        _in_flight.pop(sid, None)


def is_chat_job_in_flight(sid: Optional[str]) -> bool:
    """同一 sid のチャット処理が進行中か（ロックは取らない）。"""
    if not sid:
        return False
    now = time.monotonic()
    with _lock:
        _prune_stale(now)
        return sid in _in_flight
