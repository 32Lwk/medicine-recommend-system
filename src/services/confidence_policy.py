"""
Physical / Ask / Emotional の低確信ルーティング方針 — ConfidenceGate と整合。

ConfidenceGate（apply_confidence_gate）の unresolved path:
  1. 閾値未満 → 再トリアージ（retry_triage_with_fallback_model）
  2. 再トリアージ後も閾値未満 → 初回は確認質問（triage_clarify_sent）
  3. 確認済みまたは意味不明入力 → session["_confidence_gate_concierge"] = True

オーケストレーター / カテゴリルートは、上記 unresolved 状態では
Physical / Ask / Emotional への直接ルートを抑止し、post_pipeline の
Concierge フォールバックまたは legacy category_route へ委譲する。
"""
from __future__ import annotations

from typing import Any

_MEDICAL_CATEGORIES = frozenset({"Physical", "Emotional", "Ask"})


def should_defer_category_routing(
    category: str,
    confidence: float,
    session: Any = None,
) -> bool:
    """
    ConfidenceGate 後も低確信のまま残った場合、カテゴリ直接ルートを抑止する。

    Emotional のみ特別扱いしていた旧ロジックを Physical / Ask にも統一。
    """
    if session and session.get("_confidence_gate_concierge"):
        return True

    from config.routing_config import triage_confidence_threshold

    if category in _MEDICAL_CATEGORIES and confidence < triage_confidence_threshold():
        return True
    return False
