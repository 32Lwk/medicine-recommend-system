"""
チャット重処理用の専用スレッドプール（Starlette のスレッドプール枯渇を防ぐ）
"""
from __future__ import annotations

import atexit
import os
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_DEFAULT_CHAT_WORKERS = 4


def resolve_chat_max_workers() -> int:
    """CHAT_WORKER_MAX / CHAT_MAX_WORKERS で上書き可能（既定 4）。

    GUNICORN_WORKERS とは独立させる。SSE 経路は executor 内で sync pipeline を走らせるが、
    将来の二重 submit や並行 SSE には余裕が必要なため、Uvicorn worker 数に連動させない。
    """
    for key in ("CHAT_WORKER_MAX", "CHAT_MAX_WORKERS"):
        raw = os.getenv(key, "").strip()
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                pass
    return _DEFAULT_CHAT_WORKERS


_CHAT_EXECUTOR = ThreadPoolExecutor(
    max_workers=resolve_chat_max_workers(),
    thread_name_prefix="chat_job",
)


def get_chat_executor() -> ThreadPoolExecutor:
    return _CHAT_EXECUTOR


def submit_chat_job(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
    return _CHAT_EXECUTOR.submit(fn, *args, **kwargs)


@atexit.register
def _shutdown_chat_executor() -> None:
    _CHAT_EXECUTOR.shutdown(wait=False, cancel_futures=True)
