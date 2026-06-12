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
    processed_message: str,
    user_info: dict[str, Any],
    client: OpenAI,
    *,
    session_id: str | None = None,
) -> RecommendationLlmBatchResult:
    """
    NLU 解析と症状/医薬品種類分類を並列実行する。
    各タスクは既存関数をそのまま呼び、精度は単体実行と同一。
    """
    nlu_result: dict[str, Any] = {}
    analysis_result: dict[str, Any] = {}

    def _nlu_task() -> dict[str, Any]:
        return resolve_nlu_for_recommendation(
            processed_message,
            user_info,
            client,
            session_id=session_id,
        )

    def _symptom_task() -> dict[str, Any]:
        return analyze_symptoms_and_medicine_type(processed_message, client)

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
    """フォールバック用 usage_notes を最大3件並列生成（順序維持）。"""
    from src.core.medicine_logic import generate_usage_notes

    meds = recommended_medicines[:3]
    if not meds:
        return []

    symptoms_list: list[Any] = []
    if nlu_result and "symptoms" in nlu_result:
        symptoms_list = nlu_result.get("symptoms") or []

    notes_by_index: dict[int, str] = {}

    def _one(idx: int, medicine: dict[str, Any]) -> tuple[int, str]:
        medicine_with_details = medicine.copy()
        medicine_with_details.setdefault(
            "age_restriction", medicine.get("age_restriction", "情報なし")
        )
        medicine_with_details.setdefault(
            "doping_prohibited", medicine.get("doping_prohibited", "なし")
        )
        medicine_with_details.setdefault(
            "competition_category", medicine.get("competition_category", "情報なし")
        )
        medicine_with_details.setdefault(
            "conditions", medicine.get("conditions", "情報なし")
        )
        name = medicine.get("name") or medicine.get("product_name") or ""
        text = generate_usage_notes(
            name,
            medicine_with_details,
            user_info,
            symptoms=symptoms_list,
        )
        if text and text != "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。":
            return idx, f"<strong>{name}:</strong><br>{text}"
        return idx, ""

    with ThreadPoolExecutor(max_workers=min(max_workers, len(meds))) as pool:
        futures = [pool.submit(_one, i, m) for i, m in enumerate(meds)]
        for fut in futures:
            try:
                idx, note = fut.result()
                if note:
                    notes_by_index[idx] = note
            except Exception as exc:
                logger.warning("Parallel usage_notes task failed: %s", exc)

    return [notes_by_index[i] for i in sorted(notes_by_index)]
