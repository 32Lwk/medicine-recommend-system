"""
開発環境向け日次 Markdown ログ（非同期書き込み）。

出力先: log/log/yyyy-mm-dd-n.md
リクエスト処理をブロックしないよう、バックグラウンドスレッドで追記する。

推薦スコアリングの DEBUG は app.log / コンソールに残し、Markdown には載せない（既定）。
"""

from __future__ import annotations

import logging
import os
import queue
import re
import threading
import traceback
from datetime import datetime
from typing import Optional, Sequence, Tuple

_SENTINEL = object()
LogItem = Tuple[float, str, str, str, Optional[object]]

# 1リクエストあたり数千行になる推薦系 DEBUG（Markdown には不要）
DEFAULT_EXCLUDED_LOGGER_PREFIXES: Tuple[str, ...] = (
    "src.core.recommendation.",
    "src.core.scoring_utils",
    "src.core.candidate_scoring",
    "src.core.medicine_classifiers",
)

_LOG_PREFIX_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - \w+ - "
)


def _strip_formatter_prefix(message: str) -> str:
    """Formatter 付きの重複タイムスタンプ行頭を除去する。"""
    return _LOG_PREFIX_RE.sub("", message, count=1)


class _MarkdownNoiseFilter(logging.Filter):
    """推薦スコアリング等の高頻度ロガーを Markdown から除外する。"""

    def __init__(self, excluded_prefixes: Sequence[str]) -> None:
        super().__init__()
        self._excluded = tuple(excluded_prefixes)

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        for prefix in self._excluded:
            if name == prefix or name.startswith(prefix):
                return False
        return True


class DailyMarkdownFileHandler(logging.Handler):
    """log/log/yyyy-mm-dd-n.md へ非同期で開発向けログを書き込む Handler。"""

    def __init__(
        self,
        log_dir: str,
        max_bytes: int = 5 * 1024 * 1024,
        *,
        excluded_logger_prefixes: Optional[Sequence[str]] = DEFAULT_EXCLUDED_LOGGER_PREFIXES,
        compact: bool = True,
    ) -> None:
        super().__init__()
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.compact = compact
        os.makedirs(self.log_dir, exist_ok=True)
        if excluded_logger_prefixes:
            self.addFilter(_MarkdownNoiseFilter(excluded_logger_prefixes))
        self._queue: queue.Queue = queue.Queue()
        self._path_lock = threading.Lock()
        self._active_path: Optional[str] = None
        self._active_date: Optional[str] = None
        self._worker = threading.Thread(
            target=self._run_worker,
            name="daily-markdown-log",
            daemon=True,
        )
        self._worker.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if not self.filter(record):
                return
            msg = self.format(record)
            item: LogItem = (
                record.created,
                record.levelname,
                record.name,
                msg,
                record.exc_info,
            )
            self._queue.put_nowait(item)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        try:
            self._queue.put_nowait(_SENTINEL)
            self._worker.join(timeout=3.0)
        except Exception:
            pass
        super().close()

    def _run_worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is _SENTINEL:
                    break
                self._append(item)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def _format_block(
        self,
        created: float,
        level: str,
        logger_name: str,
        message: str,
        exc_info: Optional[object],
    ) -> str:
        body = _strip_formatter_prefix(message)
        if self.compact:
            ts = datetime.fromtimestamp(created).strftime("%H:%M:%S.%f")[:-3]
            short = logger_name.rsplit(".", 1)[-1]
            block = f"- `{ts}` **{level}** `{short}`: {body}\n"
        else:
            ts = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            block = f"\n### {ts} | {level} | `{logger_name}`\n\n```\n{body}\n```\n"
        if exc_info and exc_info is not True:
            tb = "".join(traceback.format_exception(*exc_info))
            if self.compact:
                block += f"\n  <details><summary>traceback</summary>\n\n```\n{tb}```\n</details>\n"
            else:
                block += f"\n**Traceback:**\n\n```\n{tb}\n```\n"
        return block

    def _append(self, item: LogItem) -> None:
        created, level, logger_name, message, exc_info = item
        path = self._resolve_path()
        block = self._format_block(created, level, logger_name, message, exc_info)
        with open(path, "a", encoding="utf-8") as f:
            if os.path.getsize(path) == 0:
                day = datetime.fromtimestamp(created).strftime("%Y-%m-%d")
                f.write(f"# Development log {day}\n\n")
            f.write(block)

    def _resolve_path(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._path_lock:
            if (
                self._active_path
                and self._active_date == today
                and os.path.exists(self._active_path)
                and os.path.getsize(self._active_path) < self.max_bytes
            ):
                return self._active_path

            n = 1
            while True:
                candidate = os.path.join(self.log_dir, f"{today}-{n}.md")
                if not os.path.exists(candidate):
                    self._active_path = candidate
                    self._active_date = today
                    return candidate
                if os.path.getsize(candidate) < self.max_bytes:
                    self._active_path = candidate
                    self._active_date = today
                    return candidate
                n += 1
