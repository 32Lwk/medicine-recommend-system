"""Concierge 公式 doc 回答の機械的フォールバック（LLM 失敗時・創作なし）。"""
from __future__ import annotations

import re
from typing import List


def extract_doc_bullet_excerpt(doc_body: str, *, max_items: int = 7) -> List[str]:
    """Markdown 本文から箇条書き・見出し直下の要点行を抽出。"""
    items: List[str] = []
    for line in (doc_body or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = re.sub(r"^#+\s*", "", stripped).strip()
            if len(heading) >= 4:
                items.append(heading)
            continue
        m = re.match(r"^[-*・]\s+(.+)$", stripped)
        if m:
            text = m.group(1).strip()
            if len(text) >= 6:
                items.append(text)
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            text = re.sub(r"^\d+[.)]\s+", "", stripped).strip()
            if len(text) >= 6:
                items.append(text)
    seen: set[str] = set()
    unique: List[str] = []
    for item in items:
        key = item[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= max_items:
            break
    return unique


def build_doc_excerpt_answer(
    title: str,
    doc_body: str,
    *,
    user_text: str = "",
    include_info_hint: bool = True,
) -> str:
    """ドキュメント excerpt のみでプレーン回答を組み立てる。"""
    bullets = extract_doc_bullet_excerpt(doc_body)
    if not bullets:
        return ""

    lines = [f"「{title}」について、公開ドキュメントの要点をお伝えします。"]
    if user_text.strip():
        lines.append(f"（ご質問: {user_text.strip()[:80]}）")
    lines.append("")
    for b in bullets:
        lines.append(f"・{b}")
    if include_info_hint:
        lines.append("")
        lines.append(
            "詳細は画面右上の ℹ️ から各種ドキュメントの全文をご確認いただけます。"
        )
    return "\n".join(lines)
