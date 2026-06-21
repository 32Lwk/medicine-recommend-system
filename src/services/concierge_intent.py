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

    "hey",

    "yo",

    "good morning",

    "good evening",

    # カジュアル挨拶（短い入力で症状不明判定されやすいもの）

    "やあ",

    "やー",

    "やっほ",

    "やっほー",

    "やほ",

    "よー",

    "うい",

    "うぃ",

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


# トリアージ LLM を省略できるメタ意図（キーワードで十分に確度高いもの）
_PRE_TRIAGE_META_INTENTS = frozenset({
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
})

_META_PROBE_RULES: list[tuple[re.Pattern[str], ConciergeIntent]] = [
    (re.compile(r"(あなた|あんた)(について|は誰|って何|は何|のこと)"), "app_about"),
    (re.compile(r"自己紹介"), "app_about"),
    (re.compile(r"(このツール|このアプリ|このボット)(について|とは|は何)"), "app_about"),
    (re.compile(r"(マルチエージェント|薬はどうやって|選び方の仕組み|内部構成)"), "architecture"),
    (re.compile(r"(何ができる|できること|対応言語)"), "capabilities"),
    (re.compile(r"プライバシー|個人情報"), "doc_privacy"),
    (re.compile(r"利用規約|免責|禁止事項"), "doc_terms"),
    (re.compile(r"(運営者|連絡先|お問い合わせ|不具合.{0,4}報告)"), "doc_operator"),
    (re.compile(r"(PMDA|厚労省|#7119|相談先|相談窓口)"), "doc_consultation"),
    (re.compile(r"(アプリの概要|開発背景|β版|ベータ版)"), "doc_app_overview"),
]


def probe_meta_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:
    """
    メタ質問のキーワードプローブ。LLM トリアージ・meta_triage を省略する高速パス用。
    医薬品相談・症状入力は None。
    """
    text = (user_text or "").strip()
    if not text or _is_medicine_consultation(text):
        return None
    if len(text) > 120:
        return None
    for pattern, intent in _META_PROBE_RULES:
        if pattern.search(text):
            return intent
    return None


def resolve_pre_triage_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:
    """挨拶・感謝・キーワード確定メタ意図。トリアージ前ルート対象なら intent を返す。"""
    fast = classify_concierge_intent(user_text)
    if fast in _PRE_TRIAGE_META_INTENTS:
        return fast
    probed = probe_meta_concierge_intent(user_text)
    if probed in _PRE_TRIAGE_META_INTENTS:
        return probed
    return None


def should_reset_off_topic(text: str) -> bool:

    if is_symptom_input(text):

        return True

    medicine_hints = ("薬", "医薬品", "otc", "市販", "服用", "飲ん", "副作用")

    t = text.lower()

    return any(h in t for h in medicine_hints)


