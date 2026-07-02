"""IntentRouter shadow mismatch 分類（Phase 4a-1 観測用）。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from src.dialogue.routing.types import RouteDecision

MismatchKind = Literal["regression", "gate_improvement", "exempt"]

_TRIAGE_EXPECTED_ROUTE: dict[str, str] = {
    "Physical": "Physical",
    "Emergency": "Emergency",
    "Emotional": "Counseling",
    "Ask": "Physical",
    "Other": "Concierge",
}

_GATE_IMPROVEMENT_RESOLVED_BY = frozenset({"gate", "guard"})


def expected_route_for_triage(triage_category: str) -> Optional[str]:
    return _TRIAGE_EXPECTED_ROUTE.get(triage_category or "")


def _dialogue_flags(session: Any) -> dict[str, Any]:
    if session is None or not hasattr(session, "get"):
        return {}
    try:
        from src.dialogue.context import load_dialogue_context

        return dict(load_dialogue_context(session).get("flags") or {})
    except Exception:
        return {}


def _is_session_ops_agreement(decision: RouteDecision, triage: dict[str, Any]) -> bool:
    if decision.primary_route != "SessionOps" or triage.get("category") != "Other":
        return False
    sub = str(triage.get("subcategory") or "").lower()
    session_intent = str(triage.get("session_intent") or "").lower()
    return "session_admin" in sub or session_intent in ("delete", "summarize", "status")


def _is_exempt(
    decision: RouteDecision,
    triage: dict[str, Any],
    flags: dict[str, Any],
    session: Any = None,
) -> bool:
    triage_cat = str(triage.get("category") or "")
    if (
        decision.primary_route == "Physical"
        and flags.get("pending_cancelled_by_physical")
        and triage_cat in ("Physical", "Ask", "Other")
    ):
        return True
    if (
        flags.get("fever_context")
        and triage_cat == "Other"
        and decision.primary_route == "Physical"
    ):
        return True
    if _is_counseling_followup_exempt(decision, triage, session):
        return True
    return False


def _is_counseling_followup_exempt(
    decision: RouteDecision,
    triage: dict[str, Any],
    session: Any,
) -> bool:
    """
  counseling 文脈フォローアップ（期間・状況回答）で Router が Counseling を選び
  triage が Ask/Physical のままのケース。PRIMARY ON では意図的な改善であり regression ではない。
  新規 regex は追加せず、既存 session.counseling_mode と gate source のみ参照。
    """
    if decision.primary_route != "Counseling":
        return False
    if str(triage.get("category") or "") not in ("Ask", "Physical"):
        return False
    source = str(decision.source or "")
    if source in ("counseling_pending_answer", "counseling_continue"):
        return True
    if session is not None and hasattr(session, "get"):
        mode = session.get("counseling_mode")
        if isinstance(mode, dict) and mode.get("active"):
            return True
    return False


def _is_gate_improvement(decision: RouteDecision, triage: dict[str, Any]) -> bool:
    if str(triage.get("category") or "") != "Other":
        return False
    if decision.primary_route not in ("Physical", "Store"):
        return False
    return str(decision.resolved_by or "") in _GATE_IMPROVEMENT_RESOLVED_BY


def classify_shadow_mismatch(
    decision: RouteDecision,
    triage: dict[str, Any],
    session: Any = None,
) -> tuple[bool, Optional[MismatchKind]]:
    """
    shadow mismatch 判定と理由タグ。

    Returns:
        (mismatch, mismatch_kind) — 一致時は (False, None)。
        exempt 時は (False, "exempt")。
    """
    triage_cat = str(triage.get("category") or "")
    expected = expected_route_for_triage(triage_cat)
    if not expected:
        return False, None

    flags = _dialogue_flags(session)

    if _is_exempt(decision, triage, flags, session):
        return False, "exempt"

    if _is_session_ops_agreement(decision, triage):
        return False, None

    if triage_cat == "Ask" and decision.primary_route == "Physical":
        return False, None

    if decision.primary_route == expected:
        return False, None

    if _is_gate_improvement(decision, triage):
        return True, "gate_improvement"

    return True, "regression"


def _is_counseling_followup_exempt_row(row: dict[str, Any]) -> bool:
    """JSONL 行から counseling フォローアップ exempt を推論（session 無し時）。"""
    if str(row.get("primary_route") or "") != "Counseling":
        return False
    if str(row.get("triage_category") or "") not in ("Ask", "Physical", "Other"):
        return False
    source = str(row.get("source") or "")
    sub = str(row.get("sub_route") or "")
    if source in ("counseling_pending_answer", "counseling_continue"):
        return True
    if sub in ("counseling_continue", "emotional_support"):
        return True
    try:
        from src.dialogue.routing.gate import _looks_like_counseling_followup_answer

        if _looks_like_counseling_followup_answer(str(row.get("user_input") or "")):
            return True
    except ImportError:
        pass
    return False


def infer_mismatch_kind_from_log(row: dict[str, Any]) -> Optional[MismatchKind]:
    """既存 JSONL（mismatch_kind 無し）の後方互換推論。"""
    flags = row.get("dialogue_flags") or {}
    triage_cat = str(row.get("triage_category") or "")
    primary = str(row.get("primary_route") or "")
    resolved_by = str(row.get("resolved_by") or "")

    if not row.get("mismatch"):
        if flags.get("fever_context") and triage_cat == "Other" and primary == "Physical":
            return "exempt"
        if flags.get("pending_cancelled_by_physical") and primary == "Physical":
            return "exempt"
        return None

    if _is_counseling_followup_exempt_row(row):
        return "exempt"

    stored = row.get("mismatch_kind")
    if stored in ("regression", "gate_improvement", "exempt"):
        return stored  # type: ignore[return-value]

    if triage_cat == "Other" and primary in ("Physical", "Store"):
        if resolved_by in _GATE_IMPROVEMENT_RESOLVED_BY:
            return "gate_improvement"

    return "regression"
