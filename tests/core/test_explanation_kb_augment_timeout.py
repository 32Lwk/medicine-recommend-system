"""explain バッチ KB augment のタイムアウトが RAG 完了を待たないこと。"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest


def test_augment_timeout_returns_without_waiting_for_slow_rag(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")

    def _slow_augment(*_args, **_kwargs):
        time.sleep(5.0)
        return "should not reach"

    with patch(
        "src.services.bedrock_kb_retrieve.augment_medicine_prompt_with_kb",
        side_effect=_slow_augment,
    ), patch(
        "src.services.local_rag_index.is_bm25_index_ready",
        return_value=True,
    ):
        from src.core.explanation_generator import _augment_medicine_prompt_with_timeout

        t0 = time.perf_counter()
        out = _augment_medicine_prompt_with_timeout(
            "のどが痛い",
            "base prompt",
            recommended_medicines=[{"product_name": "テスト薬"}],
            timeout_sec=0.2,
        )
        elapsed = time.perf_counter() - t0

    assert out == "base prompt"
    assert elapsed < 2.0, f"timeout path blocked for {elapsed:.2f}s"


def test_augment_skips_when_local_index_not_ready(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")

    with patch(
        "src.services.bedrock_kb_retrieve.augment_medicine_prompt_with_kb",
    ) as mock_augment, patch(
        "src.services.local_rag_index.is_bm25_index_ready",
        return_value=False,
    ):
        from src.core.explanation_generator import _augment_medicine_prompt_with_timeout

        out = _augment_medicine_prompt_with_timeout(
            "のどが痛い",
            "base prompt",
            recommended_medicines=[{"product_name": "テスト薬"}],
            timeout_sec=15.0,
        )

    assert out == "base prompt"
    mock_augment.assert_not_called()
