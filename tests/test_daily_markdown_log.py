"""日次 Markdown ログ Handler のテスト。"""

import logging
import os
import tempfile
import time

from src.utils.daily_markdown_log import (
    DEFAULT_EXCLUDED_LOGGER_PREFIXES,
    DailyMarkdownFileHandler,
)


def _wait_for_queue(handler: DailyMarkdownFileHandler, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if handler._queue.empty():
            time.sleep(0.05)
            if handler._queue.empty():
                return
        time.sleep(0.02)


def test_daily_markdown_log_writes_dated_file():
    with tempfile.TemporaryDirectory() as tmp:
        handler = DailyMarkdownFileHandler(
            tmp, excluded_logger_prefixes=(), compact=True
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.INFO)

        log = logging.getLogger("test.daily_md")
        log.setLevel(logging.INFO)
        log.addHandler(handler)
        log.info("hello markdown")

        _wait_for_queue(handler)
        handler.close()

        files = [f for f in os.listdir(tmp) if f.endswith(".md")]
        assert len(files) == 1
        content = open(os.path.join(tmp, files[0]), encoding="utf-8").read()
        assert "hello markdown" in content
        assert "**INFO**" in content


def test_excludes_recommendation_scoring_debug_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        handler = DailyMarkdownFileHandler(tmp)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        handler.setLevel(logging.DEBUG)

        noisy = logging.getLogger("src.core.recommendation.final_score_calculator")
        noisy.setLevel(logging.DEBUG)
        noisy.addHandler(handler)
        noisy.debug("should not appear")

        useful = logging.getLogger("src.handlers.chat_handler")
        useful.setLevel(logging.DEBUG)
        useful.addHandler(handler)
        useful.debug("should appear")

        _wait_for_queue(handler)
        handler.close()

        files = [f for f in os.listdir(tmp) if f.endswith(".md")]
        assert files
        content = open(os.path.join(tmp, files[0]), encoding="utf-8").read()
        assert "should not appear" not in content
        assert "should appear" in content


def test_default_excluded_prefixes_cover_scoring_modules():
    names = (
        "src.core.recommendation.final_score_calculator",
        "src.core.scoring_utils",
        "src.core.candidate_scoring",
        "src.core.medicine_classifiers",
    )
    for name in names:
        assert any(
            name == p or name.startswith(p) for p in DEFAULT_EXCLUDED_LOGGER_PREFIXES
        )
