"""推奨履歴なしの医薬品副作用 Q&A ルーティング判定。"""
from __future__ import annotations

import re
from typing import Optional

from src.dialogue.routing.context_signals import (
    extract_drug_entities,
    extract_side_effect_subject,
    is_medicine_side_effect_question,
    is_symptom_drowsiness_declaration,
)

_SIDE_EFFECT_TOPIC_RE = re.compile(
    r"副作用|眠くなる|眠気|安全(?:性)?|飲んで(?:も)?(?:いい|良い)|"
    r"ダメ|禁忌|注意|副作用は",
    re.IGNORECASE,
)


def is_medicine_side_effect_route(
    text: str,
    *,
    conversation_history: list | None = None,
    recommended_medicines: list | None = None,
) -> bool:
    """Physical / medicine_side_effect_qa へ振り分けるべき入力か。"""
    t = (text or "").strip()
    if not t:
        return False
    if is_symptom_drowsiness_declaration(t):
        return False
    if not is_medicine_side_effect_question(t):
        return False
    from src.services.medicine_qa_routing import (
        infer_medicine_qa_focuses,
        should_use_medicine_qa_unified,
    )

    focuses = infer_medicine_qa_focuses(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    )
    return not should_use_medicine_qa_unified(focuses)


def resolve_side_effect_query_subject(text: str) -> Optional[str]:
    return extract_side_effect_subject(text) or (
        extract_drug_entities(text)[0] if extract_drug_entities(text) else None
    )


def mentions_drowsiness_side_effect(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.search(r"眠い|眠くなる|眠気", t, re.IGNORECASE))
