"""
チャット重処理用の専用スレッドプール（Starlette のスレッドプール枯渇を防ぐ）
"""
from __future__ import annotations

import atexit
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_CHAT_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chat_job")


def get_chat_executor() -> ThreadPoolExecutor:
    return _CHAT_EXECUTOR


def submit_chat_job(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
    return _CHAT_EXECUTOR.submit(fn, *args, **kwargs)


@atexit.register
def _shutdown_chat_executor() -> None:
    _CHAT_EXECUTOR.shutdown(wait=False, cancel_futures=True)
