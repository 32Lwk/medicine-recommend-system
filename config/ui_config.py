"""
ユーザー画面 UI バリアント（Sage Terrace）

デフォルトは Sage Terrace UI。ロールバック:
  - LEGACY_UI_FALLBACK=true … 全体を legacy に固定
  - ?ui=legacy / Cookie ui_variant=legacy … 個別 QA 用
"""
from __future__ import annotations

import os
from typing import Literal

from config.llm_config import _get_bool

UI_VARIANT_LEGACY = "legacy"
UI_VARIANT_SAGE = "sage"
UiVariant = Literal["legacy", "sage"]

# 互換のため残すが resolve_ui_variant では参照しない（常時 Sage がデフォルト）
UI_SAGE_TERRACE_ENABLED = _get_bool("UI_SAGE_TERRACE_ENABLED", True)
LEGACY_UI_FALLBACK = _get_bool("LEGACY_UI_FALLBACK", False)

UI_VARIANT_COOKIE = "ui_variant"
UI_VARIANT_QUERY = "ui"


def resolve_ui_variant(
    *,
    query_ui: str | None = None,
    cookie_ui: str | None = None,
) -> UiVariant:
    """
    優先順位: LEGACY_UI_FALLBACK → クエリ ?ui=sage|legacy → Cookie → sage（デフォルト）
    """
    if LEGACY_UI_FALLBACK:
        return UI_VARIANT_LEGACY

    for raw in (query_ui, cookie_ui):
        if raw is not None:
            v = str(raw).strip().lower()
            if v in (UI_VARIANT_SAGE, "sage-terrace", "54"):
                return UI_VARIANT_SAGE
            if v in (UI_VARIANT_LEGACY, "classic", "01"):
                return UI_VARIANT_LEGACY

    return UI_VARIANT_SAGE


def ui_variant_cookie_max_age() -> int:
    return int(os.getenv("UI_VARIANT_COOKIE_MAX_AGE", "604800"))  # 7 days
