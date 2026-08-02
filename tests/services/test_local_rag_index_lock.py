"""Local RAG BM25 index の排他構築と ready 判定。"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

from src.services.local_rag_index import (
    BM25Index,
    clear_bm25_index,
    get_bm25_index,
    is_bm25_index_ready,
)


def setup_function():
    clear_bm25_index()


def teardown_function():
    clear_bm25_index()


def test_is_bm25_index_ready_false_until_built():
    assert is_bm25_index_ready("medicine") is False

    fake = BM25Index()
    fake.build([])

    with patch("src.services.local_rag_index._build_medicine_chunks", return_value=[]):
        get_bm25_index("medicine")

    assert is_bm25_index_ready("medicine") is True


def test_get_bm25_index_builds_once_under_concurrency():
    build_count = 0

    def _counting_build():
        nonlocal build_count
        build_count += 1
        time.sleep(0.05)
        return []

    with patch(
        "src.services.local_rag_index._build_medicine_chunks",
        side_effect=_counting_build,
    ):
        errors: list[Exception] = []

        def _worker():
            try:
                get_bm25_index("medicine")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

    assert not errors
    assert build_count == 1
