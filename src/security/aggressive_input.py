"""
攻撃的・脅迫的入力の検出と統一応答文言。

絶対ブロック（しね等）と、曖昧語を含む脅迫表現（殺すぞ等）の両方で
同じトーンの案内文を返す方針の単一ソース。
"""
from __future__ import annotations

import re
from typing import Tuple

AGGRESSIVE_INPUT_NOTICE_TITLE = "入力について"
AGGRESSIVE_INPUT_NOTICE_MESSAGE = (
    "攻撃的な表現にはお答えできません。"
    "お体の不調や市販薬のご相談があれば、お気軽にお書きください。"
)

NUMERIC_SLANG = ["69", "88", "419"]

AMBIGUOUS_KEYWORDS = [
    "やばい",
    "ヤバい",
    "草",
    "くさ",
    "クサ",
    "H",
    "h",
    "尊い",
    "たっふい",
    "タッフイ",
    "ワロタ",
    "わろた",
]

_JP_BOUNDARY_BEFORE = r"(?:^|[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff])"
_JP_BOUNDARY_AFTER = r"(?:[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]|$)"

_THREAT_KILL_PATTERN = re.compile(
    r"殺(す|せ|して)(ぞ|よ|わ|な|やる|あげる|てやる|てあげる)?|"
    r"ぶっ殺す|ぶち殺す|殺してやる|殺してあげる"
)


def _normalize_message(text: str) -> str:
    try:
        from src.services.counseling_response import normalize_text

        return normalize_text(text)
    except ImportError:
        return (text or "").strip()


def _jp_keyword_match(normalized: str, keyword: str) -> bool:
    norm_kw = _normalize_message(keyword)
    if not norm_kw:
        return False
    if len(keyword) <= 3 or keyword in AMBIGUOUS_KEYWORDS:
        pattern = _JP_BOUNDARY_BEFORE + re.escape(norm_kw) + _JP_BOUNDARY_AFTER
        return bool(re.search(pattern, normalized))
    return norm_kw in normalized


def _matches_numeric_slang(normalized: str) -> str:
    for num_slang in NUMERIC_SLANG:
        pattern = r"(?:^|[^\d])" + re.escape(num_slang) + r"(?:[^\d]|$)"
        if re.search(pattern, normalized):
            return num_slang
    return ""


def _matches_threat_kill(text: str, normalized: str) -> bool:
    if not _THREAT_KILL_PATTERN.search(normalized):
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal
    except ImportError:
        return True
    return not has_explicit_symptom_signal(text)


def _matches_inappropriate_keywords(text: str, normalized: str) -> str:
    try:
        from config.keywords import (
            ABSOLUTE_BLOCK_AMBIGUOUS,
            ABSOLUTE_BLOCK_EXCLUSIONS,
            INAPPROPRIATE_MESSAGE_KEYWORDS,
        )
    except ImportError:
        return ""

    ambiguous = set(ABSOLUTE_BLOCK_AMBIGUOUS)
    excluded = set(ABSOLUTE_BLOCK_EXCLUSIONS)

    for keyword in INAPPROPRIATE_MESSAGE_KEYWORDS:
        if not keyword or keyword in excluded:
            continue
        if keyword in ambiguous:
            if keyword in ("殺す", "殺して"):
                continue
            if _jp_keyword_match(normalized, keyword):
                return keyword
            continue
        if _jp_keyword_match(normalized, keyword):
            return keyword
    return ""


def is_aggressive_expression(text: str) -> Tuple[bool, str]:
    """攻撃的・脅迫的入力か（絶対ブロック含む）。"""
    if not text or not isinstance(text, str):
        return False, ""

    try:
        from src.security.absolute_blocklist import is_absolutely_blocked

        blocked, reason = is_absolutely_blocked(text)
        if blocked:
            return True, reason
    except ImportError:
        pass

    stripped = text.strip()
    if not stripped:
        return False, ""

    normalized = _normalize_message(stripped)

    num_hit = _matches_numeric_slang(normalized)
    if num_hit:
        return True, num_hit

    if _matches_threat_kill(stripped, normalized):
        return True, "threat_kill"

    keyword_hit = _matches_inappropriate_keywords(stripped, normalized)
    if keyword_hit:
        return True, keyword_hit

    return False, ""


def is_non_absolute_aggressive_expression(text: str) -> Tuple[bool, str]:
    """絶対ブロック以外の攻撃的入力（inappropriate ルート用）。"""
    try:
        from src.security.absolute_blocklist import is_absolutely_blocked

        if is_absolutely_blocked(text)[0]:
            return False, ""
    except ImportError:
        pass

    aggressive, reason = is_aggressive_expression(text)
    if aggressive:
        return True, reason
    return False, ""


def detect_aggressive_expression(text: str) -> bool:
    return is_aggressive_expression(text)[0]
