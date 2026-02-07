"""
絶対ブロックリストモジュール

医療的価値がなく、100%不適切として即座にはじくべき表現を定義する。
config.keywords.INAPPROPRIATE_MESSAGE_KEYWORDS を活用し、
医学的に有用な表現は除外してブロック判定する。
"""
import re
import logging
from typing import Tuple, List, Set

logger = logging.getLogger(__name__)

# 100%ブロック用の追加正規表現パターン（キーワードに含まれない脅迫・攻撃等）
_ADDITIONAL_BLOCK_PATTERNS = [
    r'ぶっ殺す', r'ぶち殺す', r'ぶった斬る', r'殴り殺す',
    r'爆破する', r'爆弾を', r'焼き討ち',
    r'kill\s+you', r"i'll\s+kill", r'gonna\s+kill\s+you',
    r'die\s+slowly', r'die\s+now', r'go\s+die',
    r'サーバー.*落とす', r'システム.*破壊', r'ddos', r'ハッキング',
]

_compiled_patterns = None
_block_keywords_set = None


def _get_block_keywords() -> Set[str]:
    """絶対ブロック対象キーワード（INAPPROPRIATE_MESSAGE_KEYWORDS から除外後）"""
    global _block_keywords_set
    if _block_keywords_set is None:
        try:
            from config.keywords import (
                INAPPROPRIATE_MESSAGE_KEYWORDS,
                ABSOLUTE_BLOCK_EXCLUSIONS,
                ABSOLUTE_BLOCK_AMBIGUOUS,
            )
            exclude = set(ABSOLUTE_BLOCK_EXCLUSIONS + ABSOLUTE_BLOCK_AMBIGUOUS)
            _block_keywords_set = {
                kw for kw in INAPPROPRIATE_MESSAGE_KEYWORDS
                if kw.strip() and kw not in exclude
            }
        except ImportError:
            _block_keywords_set = set()
    return _block_keywords_set


def _get_compiled_patterns() -> List[re.Pattern]:
    global _compiled_patterns
    if _compiled_patterns is None:
        _compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in _ADDITIONAL_BLOCK_PATTERNS
        ]
    return _compiled_patterns


def is_absolutely_blocked(text: str) -> Tuple[bool, str]:
    """
    100%ブロック対象かどうかを判定する。
    config.keywords.INAPPROPRIATE_MESSAGE_KEYWORDS を活用し、
    医学的に有用な表現（ABSOLUTE_BLOCK_EXCLUSIONS）はブロックしない。

    Args:
        text: ユーザー入力テキスト

    Returns:
        (ブロックするか, マッチしたパターンまたは空文字)
    """
    if not text or not isinstance(text, str):
        return False, ""

    stripped = text.strip()
    if not stripped:
        return False, ""

    # 追加の正規表現パターンチェック
    for pattern in _get_compiled_patterns():
        if pattern.search(stripped):
            logger.warning(f"🚫 絶対ブロックリストにマッチ: pattern={pattern.pattern[:30]}...")
            return True, pattern.pattern

    # キーワードマッチング（config.keywords を活用）
    try:
        from src.services.counseling_response import normalize_text
    except ImportError:
        normalize_text = lambda s: s

    normalized = normalize_text(stripped)
    block_keywords = _get_block_keywords()

    for keyword in block_keywords:
        if not keyword or len(keyword) <= 1:
            continue
        norm_kw = normalize_text(keyword)
        if len(keyword) <= 3:
            pattern = r'(?:^|[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff])' + re.escape(norm_kw) + r'(?:[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]|$)'
            if re.search(pattern, normalized):
                logger.warning(f"🚫 絶対ブロックリストにマッチ: keyword={keyword}")
                return True, keyword
        else:
            if norm_kw in normalized:
                logger.warning(f"🚫 絶対ブロックリストにマッチ: keyword={keyword}")
                return True, keyword

    return False, ""
