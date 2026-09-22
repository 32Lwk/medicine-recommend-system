"""Low-level SessionOps intent classification (keyword / triage hints).

Lives under ``src.core`` so importing it does not execute ``src.dialogue``
package ``__init__`` (avoids session_agent ↔ dialogue cycle).

Dependency rule:
  memory_delete / meta-concierge (lazy) → this module
        ↓
  session_agent (handlers) / pre_route_signals (signal bag)

This module must NOT import:
  - src.agents.session_agent
  - src.dialogue.routing.pre_route_signals
  - src.services.jev_eligibility
  - Jev client / LLM APIs
"""
from __future__ import annotations

import re
from typing import Any, Literal

SessionIntent = Literal["delete", "summarize", "status", "none"]
SessionOpsDetail = Literal[
    "delete", "status", "recorded_items", "summarize", "history_overview", "none"
]

_STATUS_HINTS = (
    r"ステータス",
    r"状態を教えて",
    r"状況を教えて",
    r"現在の状態",
    r"今の状態",
    r"セッション.*状態",
    r"記憶.*状態",
    r"何が記録",
    r"記録.*教えて",
    r"保存されている情報",
    r"保存されている",
)

_DESTRUCTIVE_DELETE_RE = re.compile(
    r"(消して|削除|消去|忘れて|全部消|すべて消|全て消|履歴消|記憶消|データ.*消|会話.*削除)",
    re.I,
)

_SUMMARIZE_HINTS = (
    r"履歴を要約",
    r"履歴要約",
    r"履歴を教えて",
    r"相談履歴",
    r"これまでの相談",
    r"会話を要約",
    r"チャット.*要約",
    r"要約して",
    r"まとめて",
)

_SESSION_ADMIN_LOOSE_SUMMARIZE = (
    r"要約",
    r"まとめ",
)

_SESSION_ADMIN_LOOSE_STATUS = (
    r"ステータス",
    r"状態",
    r"状況",
    r"保存されている",
    r"記録",
)

_RECORDED_ITEMS_HINTS = (
    r"何が記録",
    r"記録.*教えて",
    r"保存されている情報",
    r"保存されている",
)

_HISTORY_OVERVIEW_HINTS = (
    r"履歴を教えて",
    r"履歴を見せ",
    r"会話履歴",
)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False


def _has_destructive_delete_intent(text: str) -> bool:
    try:
        from src.agents.memory_delete_agent import _looks_like_delete_request

        if _looks_like_delete_request(text):
            return True
    except Exception:
        pass
    return bool(_DESTRUCTIVE_DELETE_RE.search(text or ""))


def _is_app_changelog_question(text: str) -> bool:
    """本アプリの CHANGELOG 案内（SessionOps の会話履歴と区別）。"""
    try:
        from src.services.concierge_intent import probe_meta_concierge_intent

        return probe_meta_concierge_intent(text) == "doc_changelog"
    except Exception:
        return False


def classify_session_intent(
    user_text: str,
    *,
    triage_result: dict[str, Any] | None = None,
) -> SessionIntent:
    """削除・要約・ステータス意図を分類する（純キーワード／triage ヒント）。"""
    t = (user_text or "").strip()
    if not t:
        return "none"

    if _is_app_changelog_question(t):
        return "none"

    if _has_destructive_delete_intent(t):
        return "delete"
    if _matches_any(t, _SUMMARIZE_HINTS):
        return "summarize"
    if _matches_any(t, _STATUS_HINTS):
        return "status"

    sub = str((triage_result or {}).get("subcategory") or "").lower()
    meta_intent = str((triage_result or {}).get("concierge_intent") or "").lower()
    session_intent = str((triage_result or {}).get("session_intent") or "").lower()
    triage_session = (
        "session_admin" in sub
        or meta_intent == "session_ops"
        or session_intent in ("delete", "summarize", "status")
    )
    if not triage_session:
        return "none"

    if session_intent in ("delete", "summarize", "status"):
        return session_intent  # type: ignore[return-value]

    if _has_destructive_delete_intent(t):
        return "delete"
    if _matches_any(t, _SESSION_ADMIN_LOOSE_SUMMARIZE):
        return "summarize"
    if _matches_any(t, _SESSION_ADMIN_LOOSE_STATUS):
        return "status"
    return "none"


def classify_session_ops_detail(
    user_text: str,
    *,
    triage_result: dict[str, Any] | None = None,
) -> SessionOpsDetail:
    """SessionOps の細分類（UX_SESSION_OPS_REAL_DATA 用）。"""
    coarse = classify_session_intent(user_text, triage_result=triage_result)
    if coarse == "delete":
        return "delete"
    t = (user_text or "").strip()
    if not t:
        return "none"
    if _matches_any(t, _RECORDED_ITEMS_HINTS):
        return "recorded_items"
    if (
        _matches_any(t, _HISTORY_OVERVIEW_HINTS)
        and not re.search(r"要約|まとめ", t)
        and not _is_app_changelog_question(t)
    ):
        return "history_overview"
    if coarse == "summarize":
        return "summarize"
    if coarse == "status":
        return "status"
    return "none"


__all__ = [
    "SessionIntent",
    "SessionOpsDetail",
    "classify_session_intent",
    "classify_session_ops_detail",
]
