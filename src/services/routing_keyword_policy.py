"""
ルーティングにおけるキーワードの役割定義。

重大問題（違法・不適切・セキュリティ・緊急）以外では、
キーワードは「候補」に留め、最終判定は文脈ゲートまたは LLM（オーケストレーター）に委ねる。
"""
from __future__ import annotations

from typing import Optional

# キーワード単独でルートを確定してよいドメイン
DECISIVE_KEYWORD_DOMAINS = frozenset({
    "security",
    "illegal_drug",
    "controlled_drug",
    "crisis",
    "emergency",
    "inappropriate",
})

# 完全一致のみ即応答可（部分一致キーワードではない）
EXACT_MATCH_GATE_DOMAINS = frozenset({
    "concierge_greeting",
    "concierge_thanks",
})


def is_decisive_keyword_domain(domain: str) -> bool:
    return domain in DECISIVE_KEYWORD_DOMAINS


def is_exact_match_gate_domain(domain: str) -> bool:
    return domain in EXACT_MATCH_GATE_DOMAINS


def keyword_finalize_allowed(
    *,
    domain: str,
    llm_confirmed: bool = False,
    context_gate_passed: bool = False,
) -> bool:
    """
    キーワードだけで応答・ルートを確定してよいか。
    重大ドメイン、または LLM 確認済みかつ文脈ゲート通過が必要。
    """
    if is_decisive_keyword_domain(domain):
        return True
    if is_exact_match_gate_domain(domain):
        return context_gate_passed
    return llm_confirmed and context_gate_passed
