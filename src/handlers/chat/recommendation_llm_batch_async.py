"""推奨フロー前半の LLM 呼び出し（async 版）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAI

from src.core.medicine_logic import analyze_symptoms_and_medicine_type
from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation
from src.handlers.chat.recommendation_llm_batch import (
    RecommendationLlmBatchResult,
    _NLU_FALLBACK,
)

logger = logging.getLogger(__name__)


async def run_nlu_and_symptom_analysis_parallel_async(
    user_text: str,
    user_info: dict[str, Any],
    client: OpenAI | AsyncOpenAI,
    *,
    session_id: str | None = None,
    session: Any = None,
) -> RecommendationLlmBatchResult:
    """NLU と症状分類を asyncio.gather で並列実行（sync 版と同一フォールバック）。"""

    async def _nlu_task() -> dict[str, Any]:
        return await asyncio.to_thread(
            resolve_nlu_for_recommendation,
            user_text,
            user_info,
            client if isinstance(client, OpenAI) else OpenAI(api_key=getattr(client, "api_key", None)),
            session_id=session_id,
            session=session,
        )

    async def _symptom_task() -> dict[str, Any]:
        sync_client = client if isinstance(client, OpenAI) else OpenAI(api_key=getattr(client, "api_key", None))
        return await asyncio.to_thread(
            analyze_symptoms_and_medicine_type,
            user_text,
            sync_client,
        )

    nlu_result: dict[str, Any] = {}
    analysis_result: dict[str, Any] = {}

    results = await asyncio.gather(_nlu_task(), _symptom_task(), return_exceptions=True)
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            label = "NLU" if idx == 0 else "Symptom"
            logger.info("%s async batch task failed: %s", label, result)
            if idx == 0:
                nlu_result = dict(_NLU_FALLBACK)
            else:
                analysis_result = {}
        elif idx == 0:
            nlu_result = result or {}
        else:
            analysis_result = result or {}

    if not nlu_result:
        nlu_result = dict(_NLU_FALLBACK)
    nlu_result.setdefault("gender_detected", {"detected": False})
    nlu_result.setdefault("pregnancy_possible", {"detected": False})
    return RecommendationLlmBatchResult(nlu_result=nlu_result, analysis_result=analysis_result)
