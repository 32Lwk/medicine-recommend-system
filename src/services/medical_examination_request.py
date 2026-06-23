"""
医療行為（診察・診断）の依頼検出。

- 完全一致フレーズ: llm_triage の高速パス（stage0）
- それ以外の言い回し: 第二段階 LLM トリアージ（inappropriate_request/medical_examination）
"""
from __future__ import annotations

import re
from typing import FrozenSet

# ユーザー入力がこのいずれかと一致（句読点のみ末尾許容）した場合に fast-path
MEDICAL_EXAMINATION_EXACT_PHRASES: FrozenSet[str] = frozenset(
    {
        "診察してください",
        "診察して",
        "診察してくれ",
        "診察してもらえますか",
        "診察お願いします",
        "診察をお願いします",
        "診てください",
        "診断してください",
        "診断して",
        "診断お願いします",
        "診断をお願いします",
        "診療してください",
        "診療して",
    }
)

_TRAILING_PUNCT = re.compile(r"[。．.!！?？]+$")


def normalize_exact_phrase(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", "", t)
    return _TRAILING_PUNCT.sub("", t)


def detect_medical_examination_request_exact(user_text: str) -> bool:
    """医療行為依頼の全文完全一致（単独フレーズのみ。複合文は LLM トリアージに委ねる）。"""
    norm = normalize_exact_phrase(user_text)
    return bool(norm) and norm in MEDICAL_EXAMINATION_EXACT_PHRASES


def triage_indicates_medical_examination(triage_result: dict | None) -> bool:
    sub = str((triage_result or {}).get("subcategory") or "").lower()
    return "inappropriate_request/medical_examination" in sub or sub.endswith(
        "/medical_examination"
    )


def resolve_medical_examination_request_type(
    user_text: str,
    triage_result: dict | None = None,
) -> str | None:
    """
    医療行為依頼種別。単独フレーズ fast-path、LLM フラグ、または subcategory。
    """
    if detect_medical_examination_request_exact(user_text):
        return "medical_examination"
    if triage_result and triage_result.get("medical_examination_request") is True:
        return "medical_examination"
    if triage_indicates_medical_examination(triage_result):
        return "medical_examination"
    return None
