"""
LINE チャット処理の排他（Gunicorn 複数ワーカー間）。

Linux では fcntl ファイルロック、それ以外ではスレッドロック（非ブロッキング）。
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_LOCK_DIR = os.environ.get("LINE_LOCK_DIR", tempfile.gettempdir())
_thread_guard = threading.Lock()
_thread_locks: dict[str, threading.Lock] = {}


class LineJobLock:
    def __init__(self) -> None:
        self._fd: Optional[int] = None
        self._thread_lock: Optional[threading.Lock] = None
        self._thread_acquired = False

    def _thread_lock_for(self, sid: str) -> threading.Lock:
        with _thread_guard:
            lock = _thread_locks.get(sid)
            if lock is None:
                lock = threading.Lock()
                _thread_locks[sid] = lock
            return lock

    def acquire(self, sid: str) -> bool:
        if sys.platform == "win32":
            lock = self._thread_lock_for(sid)
            if not lock.acquire(blocking=False):
                return False
            self._thread_lock = lock
            self._thread_acquired = True
            return True

        safe = sid.replace(":", "_").replace("/", "_")
        path = os.path.join(_LOCK_DIR, f"line-job-{safe}.lock")
        try:
            fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        except OSError as exc:
            logger.warning("LINE job lock open failed sid=%s: %s", sid, exc)
            return True
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError, OSError):
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self, sid: str) -> None:
        if self._fd is not None:
            try:
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
            return
        if self._thread_acquired and self._thread_lock is not None:
            self._thread_lock.release()
            self._thread_acquired = False
            self._thread_lock = None
