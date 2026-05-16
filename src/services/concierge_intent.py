"""ConciergeAgent 向け意図分類（高速パスのみ。メタ意図は meta_triage.py）"""

from __future__ import annotations



import re

from typing import Literal, Optional



from src.utils.input_helpers import is_symptom_input



ConciergeIntent = Literal[
    "greeting",
    "thanks",
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "chitchat",
    "redirect",
    "medical_handoff",
]



# 挨拶・感謝は完全一致（正規化後）

_EXACT_GREETINGS = frozenset({

    "こんにちは",

    "こんばんは",

    "おはよう",

    "おはようございます",

    "はじめまして",

    "初めまして",

    "hello",

    "hi",

    "good morning",

    "good evening",

})



_EXACT_THANKS = frozenset({

    "ありがとう",

    "ありがとうございます",

    "どうも",

    "どうもありがとう",

    "thanks",

    "thank you",

})



def _normalize_exact(text: str) -> str:

    t = (text or "").strip().lower()

    t = re.sub(r"\s+", "", t)

    return t





def _is_medicine_consultation(text: str) -> bool:

    t = text.lower()

    hints = (

        "薬",

        "医薬品",

        "otc",

        "市販",

        "服用",

        "飲ん",

        "副作用",

        "ドーピング",

        "競技",

        "成分",

        "飲み合わせ",

        "禁忌",

    )

    return any(h in t for h in hints)





def classify_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:

    """

    キーワードによる高速 Concierge 意図（挨拶・感謝・雑談のみ）。

    capabilities/architecture 等のメタ意図は classify_meta_concierge_intent を使用。

    """

    text = (user_text or "").strip()

    if not text:

        return None



    if _is_medicine_consultation(text):

        return None



    exact = _normalize_exact(text)

    if exact in _EXACT_GREETINGS:

        return "greeting"

    if exact in _EXACT_THANKS and len(text) < 40:

        return "thanks"



    # 雑談パターンは候補のみ（確定は meta_triage LLM）
    return None


def should_reset_off_topic(text: str) -> bool:

    if is_symptom_input(text):

        return True

    medicine_hints = ("薬", "医薬品", "otc", "市販", "服用", "飲ん", "副作用")

    t = text.lower()

    return any(h in t for h in medicine_hints)


