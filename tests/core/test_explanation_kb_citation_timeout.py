"""_kb_citation_for_explanation / retrieve timeout の回帰テスト。"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest


def test_citation_skips_when_local_index_not_ready(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")

    with patch(
        "src.services.local_rag_index.is_bm25_index_ready",
        return_value=False,
    ), patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
    ) as mock_retrieve:
        from src.core.explanation_generator import _kb_citation_for_explanation

        out = _kb_citation_for_explanation(
            {"product_name": "テスト薬"},
            {"symptoms": []},
            {"user_message": "のどが痛い"},
        )

    assert out == ""
    mock_retrieve.assert_not_called()


def test_retrieve_context_timeout_returns_empty(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")

    def _slow_retrieve(*_args, **_kwargs):
        time.sleep(5.0)
        return {"chunks": ["x"], "source_uris": []}

    with patch(
        "src.services.local_rag_index.is_bm25_index_ready",
        return_value=True,
    ), patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
        side_effect=_slow_retrieve,
    ):
        from src.core.explanation_generator import _retrieve_medicine_context_with_timeout

        t0 = time.perf_counter()
        result = _retrieve_medicine_context_with_timeout(
            "のどが痛い テスト薬",
            recommended_medicines=[{"product_name": "テスト薬"}],
            timeout_sec=0.2,
        )
        elapsed = time.perf_counter() - t0

    assert result.get("chunks") == []
    assert elapsed < 2.0
