"""Cloud Run startup: local RAG warmup must not block lifespan /health."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import main


def test_start_local_rag_warmup_returns_immediately():
    started = threading.Event()
    released = threading.Event()

    def _blocking_warmup():
        started.set()
        released.wait(timeout=2.0)

    with patch(
        "src.services.local_rag_retrieve.warmup_local_rag_index",
        side_effect=_blocking_warmup,
    ):
        t0 = time.perf_counter()
        main._start_local_rag_warmup_background()
        elapsed = time.perf_counter() - t0

    assert elapsed < 0.5, f"warmup helper blocked for {elapsed:.2f}s"
    assert started.wait(timeout=1.0), "background warmup thread did not start"
    released.set()
