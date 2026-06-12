"""recommendation_llm_batch_async のテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from src.handlers.chat.recommendation_llm_batch_async import (
    run_nlu_and_symptom_analysis_parallel_async,
)


def test_async_batch_gather_merges_results():
    nlu = {"symptoms": ["頭痛"], "gender_detected": {"detected": False}, "pregnancy_possible": {"detected": False}}
    analysis = {"medicine_type": "解熱鎮痛剤", "symptoms": ["頭痛"]}

    async def _run():
        with (
            patch(
                "src.handlers.chat.recommendation_llm_batch_async.resolve_nlu_for_recommendation",
                return_value=nlu,
            ),
            patch(
                "src.handlers.chat.recommendation_llm_batch_async.analyze_symptoms_and_medicine_type",
                return_value=analysis,
            ),
        ):
            return await run_nlu_and_symptom_analysis_parallel_async("頭が痛い", {}, MagicMock())

    batch = asyncio.run(_run())
    assert batch.nlu_result["symptoms"] == ["頭痛"]
    assert batch.analysis_result["medicine_type"] == "解熱鎮痛剤"


def test_async_batch_symptom_failure_fallback():
    nlu = {"gender_detected": {"detected": False}, "pregnancy_possible": {"detected": False}}

    async def _run():
        with (
            patch(
                "src.handlers.chat.recommendation_llm_batch_async.resolve_nlu_for_recommendation",
                return_value=nlu,
            ),
            patch(
                "src.handlers.chat.recommendation_llm_batch_async.analyze_symptoms_and_medicine_type",
                side_effect=RuntimeError("sym fail"),
            ),
        ):
            return await run_nlu_and_symptom_analysis_parallel_async("頭が痛い", {}, MagicMock())

    batch = asyncio.run(_run())
    assert batch.nlu_result["gender_detected"]["detected"] is False
    assert batch.analysis_result == {}


def test_async_batch_uses_asyncio_gather():
    async def _run():
        with patch(
            "src.handlers.chat.recommendation_llm_batch_async.asyncio.gather",
            wraps=asyncio.gather,
        ) as mock_gather:
            with (
                patch(
                    "src.handlers.chat.recommendation_llm_batch_async.resolve_nlu_for_recommendation",
                    return_value={"gender_detected": {"detected": False}, "pregnancy_possible": {"detected": False}},
                ),
                patch(
                    "src.handlers.chat.recommendation_llm_batch_async.analyze_symptoms_and_medicine_type",
                    return_value={"medicine_type": "解熱鎮痛剤", "symptoms": []},
                ),
            ):
                await run_nlu_and_symptom_analysis_parallel_async("x", {}, MagicMock())
            return mock_gather.call_count

    assert asyncio.run(_run()) == 1
