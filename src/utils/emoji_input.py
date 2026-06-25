"""Unicode 絵文字入力の検出（LINE 絵文字ルート用）。"""
from __future__ import annotations

import re
from typing import List

# Extended pictographic + よく使われる記号絵文字
_EMOJI_CHAR_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "\uFE0F"
    "\u200D"
    "]",
    flags=re.UNICODE,
)

_STRIP_FOR_EMOJI_ONLY_RE = re.compile(r"[\s！。？!?.。、,，]+")

# 侮辱・挑発として扱う絵文字（テキスト併記でも境界応答）
OFFENSIVE_EMOJI_CHARS = frozenset(
    {
        "🖕",
        "💩",
        "👹",
        "👺",
        "🤬",
        "😡",
        "🖕🏻",
        "🖕🏼",
        "🖕🏽",
        "🖕🏾",
        "🖕🏿",
    }
)


def extract_emojis(text: str) -> List[str]:
    """メッセージから絵文字シーケンスを抽出。"""
    if not text:
        return []
    return _EMOJI_CHAR_RE.findall(text)


def _cleaned_for_emoji_only_check(text: str) -> str:
    return _STRIP_FOR_EMOJI_ONLY_RE.sub("", (text or "").strip())


def is_emoji_only_message(text: str) -> bool:
    """
    空白・句読点を除き絵文字のみの入力か。
    easter-eggs.js の isEmojiOnly と同等の判定方針。
    """
    cleaned = _cleaned_for_emoji_only_check(text)
    if not cleaned:
        return False
    emojis = extract_emojis(cleaned)
    if not emojis:
        return False
    emoji_joined_len = len("".join(emojis))
    return emoji_joined_len >= len(cleaned) * 0.8


def contains_offensive_emoji(text: str) -> bool:
    """侮辱・挑発系絵文字を含むか（テキスト併記も対象）。"""
    if not text:
        return False
    for ch in text:
        if ch in OFFENSIVE_EMOJI_CHARS:
            return True
    return bool(re.search(r"🖕", text))
