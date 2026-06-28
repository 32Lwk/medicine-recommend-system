"""Stage A — 決定論的 IntentRouter gate（Wave 1b）。"""
from __future__ import annotations

from typing import Any

from src.dialogue.routing.types import RouteDecision


def run_deterministic_gate(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
) -> RouteDecision | None:
    """
    高信頼ルートのみ即決定。None = Stage B（LLM / triage マップ）へ。
    """
    text = (user_text or "").strip()
    if not text:
        return None

    triage = triage_result or {}

    from src.security.known_attack_rules import match_known_attack

    matched, rule_id = match_known_attack(text)
    if matched:
        return RouteDecision(
            primary_route="Security",
            sub_route="known_attack",
            confidence=1.0,
            resolved_by="gate",
            source=f"known_attack:{rule_id}",
        )

    from src.security.aggressive_input import is_aggressive_expression

    if is_aggressive_expression(text)[0]:
        return RouteDecision(
            primary_route="Security",
            sub_route="aggressive_input",
            confidence=1.0,
            resolved_by="gate",
            source="aggressive_input",
        )

    if (
        session is not None
        and hasattr(session, "get")
        and session.get("pending_memory_delete")
    ):
        from src.agents.session_agent import is_pending_delete_cancel

        if is_pending_delete_cancel(text):
            return RouteDecision(
                primary_route="SessionOps",
                sub_route="pending_clear",
                confidence=1.0,
                resolved_by="gate",
                source="pending_delete_cancel",
            )

    from src.agents.session_agent import probe_session_admin_intent

    session_intent = probe_session_admin_intent(text)
    if session_intent:
        pending = (
            session is not None
            and hasattr(session, "get")
            and session.get("pending_memory_delete")
        )
        if pending:
            from src.agents.session_agent import _pending_cancelled_by_medical_priority

            if _pending_cancelled_by_medical_priority(text, triage_result=triage):
                session_intent = None
        if session_intent:
            return RouteDecision(
                primary_route="SessionOps",
                sub_route=session_intent,
                confidence=1.0,
                resolved_by="gate",
                source="session_admin_probe",
            )

    if triage.get("category") == "Emergency":
        return RouteDecision(
            primary_route="Emergency",
            sub_route=str(triage.get("subcategory") or "emergency_dispatch"),
            confidence=float(triage.get("confidence") or 0.9),
            resolved_by="gate",
            source="triage_emergency",
        )

    from src.utils.input_helpers import (
        has_explicit_symptom_signal,
        has_fever_signal,
        session_has_fever_context,
    )

    if has_fever_signal(text) or (
        session is not None
        and hasattr(session, "get")
        and session_has_fever_context(session)
        and has_explicit_symptom_signal(text)
    ):
        return RouteDecision(
            primary_route="Physical",
            sub_route="fever_flow" if has_fever_signal(text) else "rule_based_recommend",
            confidence=0.95,
            resolved_by="gate",
            source="fever_or_symptom_signal",
        )

    if has_explicit_symptom_signal(text):
        return RouteDecision(
            primary_route="Physical",
            sub_route="rule_based_recommend",
            confidence=0.9,
            resolved_by="gate",
            source="symptom_signal",
        )

    from src.services.concierge_intent import classify_concierge_intent

    concierge = classify_concierge_intent(text)
    if concierge:
        return RouteDecision(
            primary_route="Concierge",
            sub_route=concierge,
            confidence=0.95,
            resolved_by="gate",
            source="concierge_fast_path",
        )

    from src.services.store_inquiry_handler import has_unambiguous_store_intent

    store_intent = has_unambiguous_store_intent(text)
    fever_active = (
        session is not None
        and hasattr(session, "get")
        and session_has_fever_context(session)
    )
    if store_intent and fever_active:
        return RouteDecision(
            primary_route="Physical",
            sub_route="fever_flow",
            confidence=0.9,
            resolved_by="gate",
            source="fever_blocks_store",
        )
    if store_intent:
        return RouteDecision(
            primary_route="Store",
            sub_route="store_locator",
            confidence=0.85,
            resolved_by="gate",
            source="store_unambiguous",
        )

    return None
