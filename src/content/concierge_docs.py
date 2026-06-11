"""ConciergeAgent 用の公式ドキュメント（docs/*.md）ローダ"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

_DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs"

DOC_INTENT_TO_FILENAME: Dict[str, str] = {
    "doc_privacy": "public/プライバシーポリシー.md",
    "doc_terms": "public/免責事項・利用規約.md",
    "doc_operator": "concierge/お問い合わせ・試験運用.md",
    "doc_consultation": "public/医薬品相談先.md",
    "doc_app_overview": "public/アプリ概要.md",
}

DOC_INTENT_TITLES: Dict[str, str] = {
    "doc_privacy": "プライバシーポリシー（試験運用版）",
    "doc_terms": "免責事項・利用規約（試験運用版）",
    "doc_operator": "お問い合わせ・試験運用について",
    "doc_consultation": "医薬品・健康相談窓口（公的情報）",
    "doc_app_overview": "アプリ概要（β版・限定公開）",
}

DOC_CONCIERGE_INTENTS: FrozenSet[str] = frozenset(DOC_INTENT_TO_FILENAME)


def is_doc_concierge_intent(intent: str) -> bool:
    return intent in DOC_CONCIERGE_INTENTS


@lru_cache(maxsize=len(DOC_INTENT_TO_FILENAME))
def load_concierge_doc(intent: str) -> Tuple[str, str]:
    """(title, markdown body) を返す。"""
    if intent not in DOC_INTENT_TO_FILENAME:
        raise KeyError(f"unknown doc intent: {intent}")
    path = _DOCS_ROOT / DOC_INTENT_TO_FILENAME[intent]
    if not path.is_file():
        raise FileNotFoundError(f"concierge doc missing: {path}")
    return DOC_INTENT_TITLES[intent], path.read_text(encoding="utf-8")
