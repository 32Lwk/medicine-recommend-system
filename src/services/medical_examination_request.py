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


# Contained-match markers for SessionOps×診察混在など（exact 専用の最短語は除外）。
# stage0 exact は変更しない。eligibility / policy_block のみがこの検出を使う。
# Worker F ATT: 「〜してほしい」系は短句 denylist 外として明示追加。
_MEDICAL_EXAMINATION_CONTAINED_MARKERS: FrozenSet[str] = frozenset(
    {
        *(
            p
            for p in MEDICAL_EXAMINATION_EXACT_PHRASES
            if len(p) >= 6
            and p not in {"診察して", "診断して", "診療して", "診てください"}
        ),
        "診察してほしい",
        "診断してほしい",
        "診てほしい",
        "医者に見てほしい",
        "診療お願いします",
        "この症状を診断",
    }
)

# BR-H01: short exact phrases are denylisted from long-marker contained set to
# limit FP, but MUST still match inside composite utterances (SessionOps mix).
_MEDICAL_EXAMINATION_SHORT_COMPOSITE_MARKERS: FrozenSet[str] = frozenset(
    {
        "診察して",
        "診断して",
        "診療して",
        "診てください",
    }
)


def detect_medical_examination_request_contained(user_text: str) -> bool:
    """医療行為依頼フレーズの部分一致（S1-G02: SessionOps 混在でも policy_block）。

    exact 検出器は複合文を意図的に False にする。eligibility と probe 抑止は
    共有関数経由で本検出を使い、Jev 対象外・SessionOps 短絡を防ぐ。
    """
    norm = normalize_exact_phrase(user_text)
    if not norm:
        return False
    if norm in MEDICAL_EXAMINATION_EXACT_PHRASES:
        return True
    if any(marker in norm for marker in _MEDICAL_EXAMINATION_CONTAINED_MARKERS):
        return True
    # Composite-only short markers (alone phrases already handled by exact set).
    if any(m in norm for m in _MEDICAL_EXAMINATION_SHORT_COMPOSITE_MARKERS):
        return True
    return False


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
