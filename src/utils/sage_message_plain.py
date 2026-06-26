"""Sage diagnosis / bot メッセージからユーザー向けプレーンテキストを復元する。"""
from __future__ import annotations

import re
from typing import Any

_SAGE_CONTENT_MARKERS = frozenset({"sage_reco", "sage_status", "sage_qa"})

_INTERNAL_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\[ステータス\]\s*[^:\n]{1,80}:\s*"),
    re.compile(r"^\[Q&A\]\s*"),
    re.compile(r"^\[推奨結果\]\s*"),
    re.compile(r"^\[推奨/ステータス表示\]\s*"),
)


def strip_internal_llm_prefix(text: str) -> str:
    """LLM 履歴圧縮用プレフィックスがユーザー向け出力に混入した場合に除去する。"""
    result = (text or "").strip()
    if not result:
        return result
    changed = True
    while changed:
        changed = False
        for pattern in _INTERNAL_PREFIX_PATTERNS:
            updated = pattern.sub("", result, count=1).strip()
            if updated != result:
                result = updated
                changed = True
                break
    return result


def diagnosis_plain_message(diagnosis: dict[str, Any]) -> str:
    """diagnosis v1 からユーザー向け本文を取り出す（内部プレフィックス除去済み）。"""
    message = strip_internal_llm_prefix(str(diagnosis.get("message") or ""))
    if message:
        return message
    for section in diagnosis.get("sections") or []:
        if not isinstance(section, dict):
            continue
        items = section.get("items") or []
        lines = [str(item).strip() for item in items if str(item).strip()]
        if lines:
            return strip_internal_llm_prefix("\n".join(lines))
    return ""


def _html_to_plain(content: str) -> str:
    if not content or "<" not in content:
        return (content or "").strip()
    try:
        from src.handlers.line.flex_messages import html_to_plain_text

        return html_to_plain_text(content)
    except Exception:
        return re.sub(r"<[^>]+>", "", content).strip()


def resolve_bot_user_facing_text(msg: dict[str, Any]) -> str:
    """bot メッセージ dict からユーザーが読むべきプレーンテキストを復元する。"""
    if not isinstance(msg, dict):
        return ""
    content = str(msg.get("content") or "").strip()
    diagnosis = msg.get("diagnosis")
    if content in _SAGE_CONTENT_MARKERS and isinstance(diagnosis, dict):
        plain = diagnosis_plain_message(diagnosis)
        if plain:
            return plain
        return ""
    if content in _SAGE_CONTENT_MARKERS:
        return ""
    plain = _html_to_plain(content)
    return strip_internal_llm_prefix(plain)
