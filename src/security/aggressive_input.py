"""
攻撃的・脅迫的入力の検出と統一応答文言。

カテゴリ別の案内文は input_block_responses を参照。
"""
from __future__ import annotations

from typing import Tuple

from src.security.input_block_responses import (
    NOTICE_BY_CATEGORY,
    match_input_block,
    should_bypass_input_block_for_counseling,
)

AGGRESSIVE_INPUT_NOTICE_TITLE = "入力について"
AGGRESSIVE_INPUT_NOTICE_MESSAGE = NOTICE_BY_CATEGORY["threat_abuse"]

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


def resolve_input_block_notice(text: str):
    """カテゴリ別ブロック案内。未ブロック時は None。"""
    return match_input_block(text)


def is_aggressive_expression(text: str) -> Tuple[bool, str]:
    """攻撃的・不適切入力か（絶対ブロック含む）。カウンセリング対象は除外。"""
    notice = match_input_block(text)
    if notice:
        return True, notice.reason
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
