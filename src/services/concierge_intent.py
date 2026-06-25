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

CONCIERGE_META_INTENTS = frozenset({
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
})



def _normalize_exact(text: str) -> str:

    t = (text or "").strip().lower()

    t = re.sub(r"\s+", "", t)

    return t





def _is_medicine_consultation(text: str) -> bool:

    t = text.lower()

    if _is_medicine_term_definition(text):
        return False

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


def _is_medicine_term_definition(text: str) -> bool:
    """用語の意味を尋ねる質問（OTC/市販薬の定義など）は医薬品相談扱いにしない。"""
    t = (text or "").strip()
    if not t:
        return False
    tl = t.lower()
    if not re.search(r"(って|とは|てなに|の意味|是什么|\?|？)", t):
        return False
    if re.search(r"otc", tl):
        return True
    if "市販薬" in t and not is_symptom_input(t):
        return True
    return False


def triage_has_concierge_meta_intent(triage_result: dict | None) -> bool:
    intent = (triage_result or {}).get("concierge_intent")
    return intent in CONCIERGE_META_INTENTS


def should_exit_counseling_for_concierge(
    user_text: str,
    *,
    triage_result: dict | None = None,
    alt_texts: list[str] | None = None,
) -> bool:
    """カウンセリング中でも Concierge に委譲すべきメタ質問か。"""
    if triage_has_concierge_meta_intent(triage_result):
        return True
    for raw in (user_text, *(alt_texts or [])):
        text = (raw or "").strip()
        if not text:
            continue
        probed = probe_meta_concierge_intent(text)
        if probed in CONCIERGE_META_INTENTS:
            return True
        if looks_like_service_identity_question(text):
            return True
        if re.search(r"(誰|だれ).{0,12}(回答|返信|答え|応答)", text):
            return True
    return False





def looks_like_user_question(text: str) -> bool:
    """ユーザーが何かを尋ねている形式か（個別フレーズ列挙なし）。"""
    t = (text or "").strip()
    if not t:
        return False
    if "?" in t or "？" in t:
        return True
    return bool(
        re.search(
            r"(ですか|ますか|でしょうか|だろうか|かな|かい|かよ|のか|んですか)$",
            t.rstrip("？?"),
        )
    )


def looks_like_service_identity_question(text: str) -> bool:
    """
    本チャット／この場所が何であるかを問う質問（近くの施設の場所案内ではない）。

    例: ここはクリニック？ / 病院ですか / 医者ですか
    非該当: 病院はどこ？ / 近くのクリニック
    """
    t = (text or "").strip()
    if not t or not looks_like_user_question(t):
        return False
    if re.search(r"(どこ|場所|近く|周辺|店内|売場)", t):
        return False
    if re.match(
        r"^(ここ|こちら|これ|この(チャット|サービス|アプリ|ツール|ボット))(は|って)",
        t,
    ):
        return True
    if re.match(r"^(あなた|あんた)(は|って)", t):
        return True
    if re.match(
        r"^(病院|医者|医師|クリニック|診療所|診察|薬局|薬屋|ドラッグストア)(ですか|ますか|かな|かい|かよ|？|\?)",
        t,
    ):
        return True
    return False


def infer_structural_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:
    """
    短い非医療・非店舗入力を構造的に greeting とみなす（辞書登録なし）。
    meta LLM スキップ時の軽量フォールバック用。質問形式は対象外。
    """
    text = (user_text or "").strip()
    if not text or len(text) > 12:
        return None
    try:
        from src.utils.emoji_input import is_emoji_only_message

        if is_emoji_only_message(text):
            return None
    except ImportError:
        pass
    try:
        from src.security.aggressive_input import is_aggressive_expression

        if is_aggressive_expression(text)[0]:
            return None
    except ImportError:
        pass
    if looks_like_user_question(text):
        return None
    if _is_medicine_consultation(text):
        return None
    from src.utils.input_helpers import has_explicit_symptom_signal

    if has_explicit_symptom_signal(text):
        return None
    store_hints = (
        "店",
        "売場",
        "在庫",
        "トイレ",
        "忘れ物",
        "営業",
        "駐車",
        "免税",
        "レジ",
        "どこ",
        "場所",
        "コンビニ",
        "薬",
        "医薬",
        "うんこ",
        "うんち",
        "おしっこ",
        "用を足",
    )
    if any(h in text for h in store_hints):
        return None
    return "greeting"


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
    (re.compile(r"(技術スタック|技術構成|開発環境|使ってる技術|tech\s*stack|デプロイ|インフラ)"), "architecture"),
    (re.compile(r"(FastAPI|Cloud\s*Run|PostgreSQL|Gunicorn|Neon)"), "architecture"),
    (re.compile(r"(何ができる|できること|対応言語)"), "capabilities"),
    (re.compile(r"otc.{0,12}(って|とは|てなに|の意味)", re.I), "capabilities"),
    (re.compile(r"市販薬.{0,12}(って|とは|てなに|の意味)"), "capabilities"),
    (re.compile(r"(誰|だれ).{0,12}(回答|返信|答え|応答)"), "architecture"),
    (re.compile(r"(今|いま).{0,12}(答え|回答|返信|応答)"), "architecture"),
    (re.compile(r"(答え|回答|返信|応答).{0,12}(誰|だれ|なに|何)"), "architecture"),
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


