"""
規制薬物リクエスト — 違法薬物と同様に即時ブロック（inappropriate_drug_block_route 参照）
"""
from __future__ import annotations

from typing import Any, Tuple

CONTROLLED_GUIDANCE_SYMPTOM = "inappropriate_request/controlled_guidance"  # legacy tests / logs

# OTC 不眠相談と衝突しうる規制薬キーワード（detect_illegal_or_controlled_drug 用）
OTC_CONTEXT_CONTROLLED_KEYWORDS = frozenset({"睡眠薬", "精神安定剤", "鎮痛薬"})


def is_otc_sleep_medicine_context(user_text: str) -> bool:
    """市販睡眠薬・不眠相談の文脈なら規制薬物判定から除外する。"""
    from src.handlers.chat.chat_emotional_route import detect_insomnia_keyword

    return detect_insomnia_keyword(user_text or "")


def should_skip_controlled_keyword(keyword: str, user_text: str) -> bool:
    if keyword not in OTC_CONTEXT_CONTROLLED_KEYWORDS:
        return False
    return is_otc_sleep_medicine_context(user_text)


def should_counsel_controlled_drug_first(session: Any) -> bool:
    return not bool(session.get("controlled_drug_counseling_done"))


def mark_controlled_drug_counseling_done(session: Any) -> None:
    session["controlled_drug_counseling_done"] = True
    if hasattr(session, "modified"):
        session.modified = True


def resolve_inappropriate_counseling_flags(
    session: Any,
    request_type: str,
) -> Tuple[bool, bool, str]:
    """
    不適切要求のカウンセリング可否を決定する。

    Returns:
        (start_counseling_mode, counseling_response, symptom_type)
    """
    symptom_type = f"inappropriate_request/{request_type}"

    if request_type in ("illegal", "controlled"):
        return False, False, symptom_type

    if request_type == "medical_examination":
        return False, True, symptom_type

    return True, True, symptom_type
