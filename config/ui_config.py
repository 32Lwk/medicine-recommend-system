"""
ユーザー画面 UI バリアント（Sage Terrace 段階移行）

段階公開手順:
  1. 開発環境で UI_SAGE_TERRACE_ENABLED=true
  2. 本番で ?ui=sage ベータ（Cookie 7日保持）
  3. 本番で UI_SAGE_TERRACE_ENABLED=true
  4. legacy コードパス削除（将来）
"""
from __future__ import annotations

import os
from typing import Literal

from config.llm_config import _get_bool

UI_VARIANT_LEGACY = "legacy"
UI_VARIANT_SAGE = "sage"
UiVariant = Literal["legacy", "sage"]

UI_SAGE_TERRACE_ENABLED = _get_bool("UI_SAGE_TERRACE_ENABLED", False)
UI_VARIANT_COOKIE = "ui_variant"
UI_VARIANT_QUERY = "ui"


def resolve_ui_variant(
    *,
    query_ui: str | None = None,
    cookie_ui: str | None = None,
) -> UiVariant:
    """
    優先順位: クエリ ?ui=sage|legacy → Cookie → 環境変数 UI_SAGE_TERRACE_ENABLED → legacy
  本番で Flag OFF のときも ?ui=sage と Cookie で QA 上書きを許可する。
    """
    for raw in (query_ui, cookie_ui):
        if raw is not None:
            v = str(raw).strip().lower()
            if v in (UI_VARIANT_SAGE, "sage-terrace", "54"):
                return UI_VARIANT_SAGE
            if v in (UI_VARIANT_LEGACY, "classic", "01"):
                return UI_VARIANT_LEGACY

    if UI_SAGE_TERRACE_ENABLED:
        return UI_VARIANT_SAGE
    return UI_VARIANT_LEGACY


def ui_variant_cookie_max_age() -> int:
    return int(os.getenv("UI_VARIANT_COOKIE_MAX_AGE", "604800"))  # 7 days
