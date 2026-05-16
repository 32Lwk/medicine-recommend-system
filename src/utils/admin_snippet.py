"""
管理画面用テキスト抜粋（一覧 / 詳細）
"""
from __future__ import annotations

import os
import re


def _max_chars(kind: str) -> int:
    if kind == "detail":
        try:
            return int(os.getenv("ADMIN_DETAIL_USER_MESSAGE_MAX_CHARS", "800"))
        except ValueError:
            return 800
    try:
        return int(os.getenv("ADMIN_LIST_SNIPPET_MAX_CHARS", "120"))
    except ValueError:
        return 120


def truncate_user_text(text: str, kind: str = "list") -> str:
    """kind: list | detail"""
    t = (text or "").strip()
    if not t:
        return ""
    limit = _max_chars(kind)
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"
