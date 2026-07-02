"""
入力ブロックのカテゴリ分類と、カテゴリ別の応答文言。

カウンセリングへ渡すべき入力（性被害の相談等）はブロックしない。
それ以外は脅迫・性的スラング・勧誘・システム攻撃などに応じた案内を返す。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# カウンセリング／危機対応ルートへ渡す（validator ではブロックしない）
COUNSELING_BYPASS_KEYWORDS = frozenset({
    "レイプ", "れいぷ", "rape", "強姦", "ごうかん",
    "性被害", "せいひがい", "性的被害", "せいてきひがい",
    "性暴力", "せいぼうりょく", "性的暴力", "せいてきぼうりょく",
    "痴漢", "ちかん",
})

THREAT_ABUSE_KEYWORDS = frozenset({
    "しね", "死ね", "しねよ", "死ねよ", "しなさい", "死なさい",
    "くたばれ", "消えろ", "消えて", "出て行け", "出て行って",
    "バカ", "アホ", "馬鹿", "阿呆", "バカヤロー", "アホウ",
    "クソ", "くそ", "糞", "クソバカ", "くそばか",
    "殺す", "殺して", "殺せ", "殺してやる", "殺してあげる",
    "死ねばいい", "死ねば", "死んで", "死なせて", "死なせろ",
})

SOLICITATION_KEYWORDS = frozenset({
    "パパ活", "ぱぱかつ", "ぱぱ活", "逆援助", "ぎゃくえんじょ",
    "sugardaddy", "sugarbaby", "sugar daddy", "sugar baby",
    "援助交際", "えんじょこうさい", "JK", "j k",
    "売春", "ばいしゅん", "風俗", "ふうぞく", "ソープ", "そーぷ",
    "デリヘル", "でりへる", "デリバリーヘルス",
    "出会い系", "であいけい", "出会い系サイト",
    "ナンパ", "なんぱ", "逆ナン", "ぎゃくなん", "ナンパする",
})

ILLEGAL_DRUG_KEYWORDS = frozenset({
    "アヘン", "あへん",
})

NUMERIC_SLANG = ("69", "88", "419")

AMBIGUOUS_KEYWORDS = frozenset({
    "やばい", "ヤバい", "草", "くさ", "クサ", "H", "h",
    "尊い", "たっふい", "タッフイ", "ワロタ", "わろた",
})

_JP_BOUNDARY_BEFORE = r"(?:^|[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff])"
_JP_BOUNDARY_AFTER = r"(?:[^\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]|$)"

_THREAT_KILL_PATTERN = re.compile(
    r"殺(す|せ|して)(ぞ|よ|わ|な|やる|あげる|てやる|てあげる)?|"
    r"ぶっ殺す|ぶち殺す|殺してやる|殺してあげる"
)

_SYSTEM_ABUSE_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"サーバー.*落とす",
        r"システム.*破壊",
        r"\bddos\b",
        r"ddos",
        r"ハッキング",
        r"爆破する",
        r"爆弾を",
        r"焼き討ち",
    )
)

_THREAT_ABUSE_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ぶっ殺す",
        r"ぶち殺す",
        r"ぶった斬る",
        r"殴り殺す",
        r"kill\s+you",
        r"i'll\s+kill",
        r"gonna\s+kill\s+you",
        r"die\s+slowly",
        r"die\s+now",
        r"go\s+die",
    )
)

NOTICE_BY_CATEGORY = {
    "threat_abuse": (
        "攻撃的な表現にはお答えできません。"
        "お体の不調や市販薬のご相談があれば、お気軽にお書きください。"
    ),
    "sexual_content": (
        "当サービスは市販薬の症状相談を目的としています。"
        "性的な内容にはお答えできません。"
        "お体の不調やお薬のことでお困りのことがあれば、お気軽にお書きください。"
    ),
    "solicitation": (
        "売買や勧誘に関するご相談にはお答えできません。"
        "お体の不調や市販薬のご相談であれば、お手伝いできます。"
    ),
    "illegal_drugs": (
        "違法な薬物に関するご相談にはお答えできません。"
        "市販薬による症状の相談であれば、お気軽にお尋ねください。"
    ),
    "system_abuse": (
        "システムへの攻撃や不正な操作を試みる入力にはお答えできません。"
        "症状や市販薬のご相談は自然な文章でお書きください。"
    ),
}

KIND_BY_CATEGORY = {
    "threat_abuse": "aggressive_input",
    "sexual_content": "inappropriate_sexual",
    "solicitation": "inappropriate_solicitation",
    "illegal_drugs": "inappropriate_illegal",
    "system_abuse": "system_abuse",
}

VARIANT_BY_CATEGORY = {
    "threat_abuse": "security",
    "sexual_content": "caution",
    "solicitation": "caution",
    "illegal_drugs": "security",
    "system_abuse": "security",
}

TITLE_BY_CATEGORY = {
    "threat_abuse": "入力について",
    "sexual_content": "ご利用について",
    "solicitation": "ご利用について",
    "illegal_drugs": "ご利用について",
    "system_abuse": "入力について",
}


@dataclass(frozen=True)
class InputBlockNotice:
    category: str
    reason: str
    message: str
    title: str
    kind: str
    variant: str


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


def should_bypass_input_block_for_counseling(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    normalized = _normalize_message(text.strip())
    if not normalized:
        return False
    lower = normalized.lower()
    for keyword in COUNSELING_BYPASS_KEYWORDS:
        if keyword.lower() in lower:
            return True
    return False


def _keyword_category(keyword: str) -> str:
    if keyword in THREAT_ABUSE_KEYWORDS:
        return "threat_abuse"
    if keyword in SOLICITATION_KEYWORDS:
        return "solicitation"
    if keyword in ILLEGAL_DRUG_KEYWORDS:
        return "illegal_drugs"
    return "sexual_content"


def _build_notice(category: str, reason: str) -> InputBlockNotice:
    return InputBlockNotice(
        category=category,
        reason=reason,
        message=NOTICE_BY_CATEGORY[category],
        title=TITLE_BY_CATEGORY[category],
        kind=KIND_BY_CATEGORY[category],
        variant=VARIANT_BY_CATEGORY[category],
    )


def _matches_threat_kill(text: str, normalized: str) -> bool:
    if not _THREAT_KILL_PATTERN.search(normalized):
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal
    except ImportError:
        return True
    return not has_explicit_symptom_signal(text)


def _matches_numeric_slang(normalized: str) -> str:
    for num_slang in NUMERIC_SLANG:
        pattern = r"(?:^|[^\d])" + re.escape(num_slang) + r"(?:[^\d]|$)"
        if re.search(pattern, normalized):
            return num_slang
    return ""


def _matches_inappropriate_keyword(text: str, normalized: str) -> Optional[InputBlockNotice]:
    try:
        from config.keywords import (
            ABSOLUTE_BLOCK_AMBIGUOUS,
            ABSOLUTE_BLOCK_EXCLUSIONS,
            INAPPROPRIATE_MESSAGE_KEYWORDS,
        )
    except ImportError:
        return None

    ambiguous = set(ABSOLUTE_BLOCK_AMBIGUOUS)
    excluded = set(ABSOLUTE_BLOCK_EXCLUSIONS)

    for keyword in INAPPROPRIATE_MESSAGE_KEYWORDS:
        if not keyword or keyword in excluded or keyword in COUNSELING_BYPASS_KEYWORDS:
            continue
        if keyword in ambiguous:
            if keyword in ("殺す", "殺して"):
                continue
            if not _jp_keyword_match(normalized, keyword):
                continue
        elif not _jp_keyword_match(normalized, keyword):
            continue
        return _build_notice(_keyword_category(keyword), keyword)
    return None


def match_input_block(text: str) -> Optional[InputBlockNotice]:
    """ブロック対象ならカテゴリ別案内を返す。カウンセリングへ渡す入力は None。"""
    if not text or not isinstance(text, str):
        return None
    if should_bypass_input_block_for_counseling(text):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    normalized = _normalize_message(stripped)

    for pattern in _SYSTEM_ABUSE_PATTERNS:
        if pattern.search(stripped):
            return _build_notice("system_abuse", pattern.pattern)

    for pattern in _THREAT_ABUSE_PATTERNS:
        if pattern.search(stripped):
            return _build_notice("threat_abuse", pattern.pattern)

    num_hit = _matches_numeric_slang(normalized)
    if num_hit:
        return _build_notice("sexual_content", num_hit)

    if _matches_threat_kill(stripped, normalized):
        return _build_notice("threat_abuse", "threat_kill")

    keyword_notice = _matches_inappropriate_keyword(stripped, normalized)
    if keyword_notice:
        return keyword_notice

    try:
        from src.security.absolute_blocklist import is_absolutely_blocked

        blocked, reason = is_absolutely_blocked(text)
        if blocked:
            return _build_notice("threat_abuse", reason)
    except ImportError:
        pass

    return None


def is_input_blocked(text: str) -> tuple[bool, str]:
    notice = match_input_block(text)
    if notice:
        return True, notice.reason
    return False, ""
