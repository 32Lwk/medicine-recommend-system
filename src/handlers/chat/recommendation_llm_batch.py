"""推奨フロー前半の LLM 呼び出しを並列実行（NLU ∥ 症状分類）。"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from src.core.medicine_logic import analyze_symptoms_and_medicine_type
from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation

logger = logging.getLogger(__name__)

_NLU_FALLBACK: dict[str, Any] = {
    "gender_detected": {"detected": False},
    "pregnancy_possible": {"detected": False},
}


@dataclass(frozen=True)
class RecommendationLlmBatchResult:
    nlu_result: dict[str, Any]
    analysis_result: dict[str, Any]


def run_nlu_and_symptom_analysis_parallel(
    user_text: str,
    user_info: dict[str, Any],
    client: OpenAI,
    *,
    session_id: str | None = None,
    session: Any = None,
) -> RecommendationLlmBatchResult:
    """
    NLU 解析と症状/医薬品種類分類を並列実行する。
    user_text は正規化前のユーザー生入力を渡すこと。
    """
    nlu_result: dict[str, Any] = {}
    analysis_result: dict[str, Any] = {}

    def _nlu_task() -> dict[str, Any]:
        return resolve_nlu_for_recommendation(
            user_text,
            user_info,
            client,
            session_id=session_id,
            session=session,
        )

    def _symptom_task() -> dict[str, Any]:
        return analyze_symptoms_and_medicine_type(user_text, client)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_nlu = pool.submit(_nlu_task)
        fut_sym = pool.submit(_symptom_task)
        try:
            nlu_result = fut_nlu.result() or {}
        except Exception as exc:
            logger.info("NLU batch task failed: %s", exc)
            nlu_result = dict(_NLU_FALLBACK)
        try:
            analysis_result = fut_sym.result() or {}
        except Exception as exc:
            logger.info("Symptom analysis batch task failed: %s", exc)
            analysis_result = {}

    if not nlu_result:
        nlu_result = dict(_NLU_FALLBACK)
    nlu_result.setdefault("gender_detected", {"detected": False})
    nlu_result.setdefault("pregnancy_possible", {"detected": False})
    return RecommendationLlmBatchResult(nlu_result=nlu_result, analysis_result=analysis_result)


def generate_usage_notes_parallel(
    recommended_medicines: list[dict[str, Any]],
    *,
    user_info: dict[str, Any],
    nlu_result: dict[str, Any] | None,
    max_workers: int = 3,
) -> list[str]:
    """フォールバック用 usage_notes（ルールベース・LLM なし）。"""
    from src.core.explanation_generator import _rule_based_individual_notes

    meds = recommended_medicines[:3]
    if not meds:
        return []

    notes = _rule_based_individual_notes(meds)
    out: list[str] = []
    for med, note in zip(meds, notes):
        name = med.get("name") or med.get("product_name") or ""
        body = note.split("\n", 1)[-1] if note else ""
        if body:
            out.append(f"<strong>{name}:</strong><br>{body}")
    return out
