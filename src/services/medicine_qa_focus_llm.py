"""Medicine QA focus — ルールが general/曖昧なときの LLM 補完（低コスト・文脈付き）。"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from src.services.medicine_qa_routing import MedicineQaFocus

logger = logging.getLogger(__name__)

_VALID_FOCUSES = frozenset({
    "comparison",
    "side_effect",
    "doping",
    "interaction",
    "usage",
    "ingredient",
    "age",
    "product_image",
    "general",
})


def is_medicine_qa_focus_llm_enabled() -> bool:
    val = os.getenv("MEDICINE_QA_FOCUS_LLM")
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def should_try_focus_llm_enrichment(
    rule_focuses: list[str],
    user_message: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """LLM 補完を試みる条件（general のみ + 文脈/質問シグナル）。"""
    if not is_medicine_qa_focus_llm_enabled():
        return False
    t = (user_message or "").strip()
    if not t:
        return False
    non_general = [f for f in rule_focuses if f != "general"]
    if non_general:
        return False
    has_context = bool(conversation_history) or bool(recommended_medicines)
    if not has_context:
        return False
    from src.services.medicine_qa_routing import _has_informational_intent, _is_anaphoric_reference

    return _has_informational_intent(t) or _is_anaphoric_reference(t)


def _format_history(history: list[dict[str, Any]] | None, *, limit: int = 6) -> str:
    if not history:
        return "(なし)"
    lines: list[str] = []
    for m in history[-limit:]:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        content = str(m.get("content") or m.get("message") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(なし)"


def _format_recommended(meds: list[dict[str, Any]] | None) -> str:
    if not meds:
        return "(なし)"
    names = [
        str(m.get("product_name") or m.get("name") or "").strip()
        for m in meds
        if isinstance(m, dict)
    ]
    names = [n for n in names if n]
    return ", ".join(names[:4]) if names else "(なし)"


def _parse_focus_response(raw: str) -> list[MedicineQaFocus]:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    focuses_raw = data.get("focuses") if isinstance(data, dict) else None
    if not isinstance(focuses_raw, list):
        return []
    out: list[MedicineQaFocus] = []
    for item in focuses_raw:
        f = str(item or "").strip()
        if f in _VALID_FOCUSES and f not in out:
            out.append(f)  # type: ignore[arg-type]
    return out


def enrich_medicine_qa_focuses_llm(
    user_message: str,
    rule_focuses: list[str],
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> list[MedicineQaFocus]:
    """LLM で focus を推定。失敗時は rule_focuses をそのまま返す。"""
    if not should_try_focus_llm_enrichment(
        rule_focuses,
        user_message,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return list(rule_focuses)  # type: ignore[arg-type]

    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return list(rule_focuses)  # type: ignore[arg-type]

    if not openai_client:
        return list(rule_focuses)  # type: ignore[arg-type]

    model = os.getenv("MEDICINE_QA_FOCUS_LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "あなたは医薬品 Q&A の意図分類器です。"
        "ユーザーの発話と会話文脈から、質問の focus を JSON のみで返してください。\n\n"
        f"ユーザー発話: {user_message}\n"
        f"推奨医薬品: {_format_recommended(recommended_medicines)}\n"
        f"会話履歴:\n{_format_history(conversation_history)}\n\n"
        "focus は次から1つ以上: comparison, side_effect, doping, interaction, "
        "usage, ingredient, age, product_image, general\n"
        "副作用の因果（飲むと眠い）は side_effect のみ。用法用量は usage。"
        "お酒・併用は interaction。競技・大会文脈は doping。\n"
        'JSON: {"focuses": ["..."], "reason": "短い理由"}'
    )
    try:
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path="medicine_qa/focus_llm",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=120,
        )
        parsed = _parse_focus_response(extract_completion_text(resp))
        if parsed and parsed != ["general"]:
            logger.info("medicine_qa_focus_llm: %s -> %s", user_message[:40], parsed)
            return parsed
    except Exception:
        logger.warning("medicine_qa_focus_llm failed", exc_info=True)
    return list(rule_focuses)  # type: ignore[arg-type]
