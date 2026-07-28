"""Concierge 回答 — ユーザー言及順の抽出とプロンプト生成（intent 横断）。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ResponseTopic:
    """ユーザー質問内で検出した話題（出現位置順）。"""

    topic_id: str
    label: str
    paragraph_hint: str = ""
    start: int = 0


_LEGAL_CROSSDOC_TOPIC_DEFS: Tuple[Tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "terms",
        re.compile(r"利用規約|免責事項|免責|規約", re.I),
        "利用規約・免責",
        "試験運用・免責・禁止事項・利用条件・知的財産・準拠法など",
    ),
    (
        "privacy",
        re.compile(r"プライバシー|プラポリ|個人情報|ポリシー", re.I),
        "プライバシーポリシー",
        "データの取得・利用目的・管理・削除権・第三者提供・匿名加工など",
    ),
)

_LEGAL_CROSSDOC_SHORT_LABELS = {
    "privacy": "プライバシー",
    "terms": "利用規約",
}

_LEGAL_CROSSDOC_DEFAULT_ORDER = ("privacy", "terms")

_PRIVACY_FALLBACK_PARA = (
    "プライバシーポリシーは、症状や属性など「どんな情報を取得し、どう利用・保管・削除するか」"
    "といったデータの扱いを定めています。"
)
_TERMS_FALLBACK_PARA = (
    "利用規約・免責は、試験運用（β版）での位置づけや免責、禁止事項など、"
    "サービスの「使い方と責任の範囲」を定めています。"
)

_FALLBACK_PARAS = {
    "privacy": _PRIVACY_FALLBACK_PARA,
    "terms": _TERMS_FALLBACK_PARA,
}


def extract_topic_mention_order(
    user_text: str,
    topic_defs: Sequence[Tuple[str, re.Pattern[str], str, str]],
) -> List[ResponseTopic]:
    """各 topic の最初の出現位置でソート（ユーザー言及順）。"""
    text = (user_text or "").strip()
    if not text:
        return []

    hits: List[ResponseTopic] = []
    seen: set[str] = set()
    for topic_id, pattern, label, hint in topic_defs:
        match = pattern.search(text)
        if not match or topic_id in seen:
            continue
        seen.add(topic_id)
        hits.append(
            ResponseTopic(
                topic_id=topic_id,
                label=label,
                paragraph_hint=hint,
                start=match.start(),
            )
        )
    hits.sort(key=lambda t: t.start)
    return hits


def extract_legal_crossdoc_topic_order(user_text: str) -> List[ResponseTopic]:
    return extract_topic_mention_order(user_text, _LEGAL_CROSSDOC_TOPIC_DEFS)


def resolve_legal_crossdoc_topic_order(user_text: str) -> List[ResponseTopic]:
    """言及が1件以下のときは既定順（privacy → terms）。"""
    ordered = extract_legal_crossdoc_topic_order(user_text)
    if len(ordered) >= 2:
        return ordered
    by_id = {t.topic_id: t for t in ordered}
    out: List[ResponseTopic] = []
    for topic_id in _LEGAL_CROSSDOC_DEFAULT_ORDER:
        if topic_id in by_id:
            out.append(by_id[topic_id])
        else:
            for tid, _pat, label, hint in _LEGAL_CROSSDOC_TOPIC_DEFS:
                if tid == topic_id:
                    out.append(ResponseTopic(topic_id=tid, label=label, paragraph_hint=hint))
                    break
    return out


def build_user_mention_order_instruction(
    user_text: str,
    *,
    intent: str = "",
    structured_topics: Optional[Sequence[ResponseTopic]] = None,
) -> str:
    """
    LLM 向け「回答順序」ブロック。
    structured_topics が2件以上あれば具体順序、なければ一般ルール。
    """
    topics = list(structured_topics or [])
    if len(topics) >= 2:
        chain = " → ".join(t.label for t in topics)
        return "\n".join(
            [
                "【回答順序 — 必須】",
                f"- ユーザーが質問文で言及した順に説明する: {chain}",
                "- テンプレートや慣習（例: プライバシーを先に）で順序を入れ替えない",
                "- 各話題は短い段落1つで述べ、説明が終わってから次の話題に移る",
            ]
        )

    if _looks_like_multi_topic_question(user_text):
        return (
            "【回答順序 — 必須】\n"
            "- ユーザーが複数の事柄・概念・ドキュメントに言及した場合、**質問文に現れた順**で説明する\n"
            "- システム都合や慣習で順序を入れ替えない\n"
            "- ユーザーが A と B の違いを聞いたとき、質問文で**先に現れた方**から説明する"
        )

    intent_key = (intent or "").strip().lower()
    if intent_key in ("doc_privacy", "doc_terms", "doc_operator", "architecture", "capabilities"):
        return (
            "【回答順序】\n"
            "- 質問に複数の論点が含まれる場合、**質問文の言及順**に沿って答える"
        )
    return ""


def _looks_like_multi_topic_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if re.search(r"違い|比較|どっち|vs|対", t, re.I):
        return True
    if t.count("と") >= 2:
        return True
    return bool(re.search(r"(.+)(?:と|や|、)(.+)(?:の|は|を).*(?:違い|比較)", t))


def build_legal_crossdoc_requirements(user_text: str) -> str:
    """横断比較用要件 — 段落順をユーザー言及順に合わせる。"""
    topics = resolve_legal_crossdoc_topic_order(user_text)
    order_block = build_user_mention_order_instruction(
        user_text,
        structured_topics=topics,
    )
    para_specs: List[str] = []
    for idx, topic in enumerate(topics[:2], start=1):
        para_specs.append(
            f"- 第{idx}段落: {topic.label}が定めること（{topic.paragraph_hint}）を1〜2文"
        )

    t0, t1 = topics[0], topics[1]
    privacy_label = t0.label if t0.topic_id == "privacy" else t1.label
    terms_label = t1.label if t1.topic_id == "terms" else t0.label
    closing_hint = (
        f"迷ったときの例: データの扱い → {privacy_label}、"
        f"使い方・責任の範囲 → {terms_label}"
    )

    return f"""【要件】
{order_block}

- 上記参照のみに基づき、**役割の違い**を説明する（条項の写し出し・一覧禁止）
- **箇条書き（・）は使わない**。短い段落（**2〜3段落**）で書く
{chr(10).join(para_specs)}
- 第{min(len(topics), 2) + 1}段落: 両者の関係と、迷ったときの見方を**やさしく**案内する（**ℹ️ 絵文字は書かない**）
  - 禁止: 「見ればよい」「確認してください」だけで突き放す短い一文
  - {closing_hint}
- 連絡先・メール・URL・氏名は**書かない**
- Markdown の ** は使わない
- 禁止: 「このドキュメントに記載がない」等の拒否、一方の md から他方の条項を創作
- **全文案内・ℹ️・「画面右上から確認」等の締めは書かない**（システムが自動付与する）
- 症状・お薬の相談促しは付けない
"""


def legal_crossdoc_card_title(user_text: str) -> str:
    topics = resolve_legal_crossdoc_topic_order(user_text)
    if len(topics) >= 2:
        a = _LEGAL_CROSSDOC_SHORT_LABELS.get(topics[0].topic_id, topics[0].label)
        b = _LEGAL_CROSSDOC_SHORT_LABELS.get(topics[1].topic_id, topics[1].label)
        return f"{a}と{b}"
    return "プライバシーと利用規約"


def append_mention_order_requirements(
    requirements: str,
    user_text: str,
    *,
    intent: str = "",
) -> str:
    """既存の要件ブロック末尾に回答順序指示を付与（空ならそのまま）。"""
    block = build_user_mention_order_instruction(user_text, intent=intent)
    if not block:
        return requirements
    return f"{requirements.rstrip()}\n\n{block}\n"


def build_legal_crossdoc_fallback_body(user_text: str, *, info_hint: str) -> str:
    """フォールバック本文 — ユーザー言及順の2段落 + 案内 + info_hint。"""
    topics = resolve_legal_crossdoc_topic_order(user_text)[:2]
    paras = [_FALLBACK_PARAS[t.topic_id] for t in topics]
    guidance = (
        f"データの保存や削除について知りたいときはプライバシーポリシーを、"
        f"サービスの利用条件や免責については利用規約・免責をご覧ください。"
    )
    return "\n\n".join([*paras, guidance, info_hint])
