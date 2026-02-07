"""
漢数字変換モジュール

日本語の漢数字表記を数値に変換する責務を持つ。
年齢表現（二十一歳、三十歳など）のパースに使用。
"""
import re
from typing import Optional


# 位の漢数字
_KANJI_DIGITS = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000,
}

# アラビア数字
_ASCII_DIGITS = set('0123456789')


def parse_kanji_age(text: str) -> Optional[int]:
    """
    テキストから漢数字または混在の年齢表現を抽出して数値を返す。

    対応例: 二十一歳, 20歳, 三十歳, 九十九歳, 二十歳
    範囲外（0未満、150以上）の場合はNoneを返す。
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip()

    # 漢数字パターン: 〇〇歳 または 〇〇才
    match = re.search(r'([〇零一二三四五六七八九十百千]+)\s*[歳才]', text)
    if match:
        kanji_part = match.group(1)
        value = _kanji_to_int(kanji_part)
        if value is not None and 0 < value < 150:
            return value

    # アラビア数字: 21歳
    match = re.search(r'(\d+)\s*[歳才]', text)
    if match:
        value = int(match.group(1))
        if 0 < value < 150:
            return value

    return None


def _kanji_to_int(kanji: str) -> Optional[int]:
    """
    漢数字文字列を整数に変換。
    例: 二十一 -> 21, 三十 -> 30, 九十九 -> 99
    """
    if not kanji:
        return None

    # 十単体は10
    if kanji == '十':
        return 10

    result = 0
    current = 0

    for i, c in enumerate(kanji):
        if c in _KANJI_DIGITS:
            v = _KANJI_DIGITS[c]
            if v >= 10:  # 十、百、千、万
                if v == 10 and current == 0:
                    current = 1
                result += current * v if current else v
                current = 0
            else:
                current = v
        else:
            return None

    result += current
    return result if result > 0 else None
