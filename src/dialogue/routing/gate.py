"""Stage A — 決定論的 IntentRouter gate（Wave 1b）。"""
from __future__ import annotations

import re
from typing import Any

from src.dialogue.routing.types import RouteDecision

_MEDICAL_EMERGENCY_HINTS = (
    "痙攣",
    "引きつけ",
    "けいれん",
    "意識がもうろう",
    "意識がない",
    "意識を失",
    "呼吸が苦しい",
    "呼吸困難",
    "呼吸ができない",
    "息ができない",
    "薬を大量",
    "大量に飲",
    "飲みすぎ",
    "過量服薬",
)

_EMOTIONAL_COUNSELING_HINTS = (
    "眠れ",
    "不眠",
    "つらい",
    "しんどい",
    "不安",
    "ストレス",
    "落ち込",
    "悩んで",
    "イライラ",
    "孤独",
    "気持ち",
    "人間関係",
    "仕事が",
    "プレッシャー",
)

_PHARMACY_LOCATION_KEYWORDS = (
    "薬局",
    "ドラッグストア",
    "マツキヨ",
    "マツモトキヨシ",
    "ウエルシア",
    "ツルハ",
    "サンドラッグ",
    "ココカラ",
    "otc",
)

_LOCATION_HINTS = (
    "近く",
    "どこ",
    "場所",
    "教えて",
    "ありますか",
    "購入",
    "買える",
    "売って",
)

_COUNSELING_FOLLOWUP_ANSWER_RE = re.compile(
    r"(\d+\s*(日|週間|ヶ月|か月|年)|"
    r"最近|昨日|今日|先週|"
    r"上司|同僚|仕事|原因|"
    r"くらいです|ほどです|程度です)",
    re.I,
)

_PHYSICAL_LIFESTYLE_FOLLOWUP_RE = re.compile(
    r"(睡眠|眠れ|寝付|運動|食事|生活習慣|お酒|タバコ|カフェイン|ストレッチ)",
    re.I,
)

_EMOTIONAL_OVERRIDE_HINTS = (
    "不安",
    "つらい",
    "落ち込",
    "ストレス",
    "眠れない",
    "不眠",
)


def _looks_like_counseling_followup_answer(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 120:
        return False
    if _COUNSELING_FOLLOWUP_ANSWER_RE.search(t):
        return True
    return len(t) <= 24 and not any(
        k in t for k in ("頭痛", "熱", "咳", "薬", "痛い", "発熱")
    )


def _looks_like_physical_lifestyle_followup(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 160:
        return False
    if any(h in t for h in _EMOTIONAL_OVERRIDE_HINTS):
        return False
    return bool(_PHYSICAL_LIFESTYLE_FOLLOWUP_RE.search(t))


def _physical_consultation_active(session: Any) -> bool:
    if session is None or not hasattr(session, "get"):
        return False
    if session.get("physical_consultation_active"):
        return True
    triage = session.get("last_triage_result") or {}
    if str(triage.get("category") or "") == "Physical":
        messages = session.get("messages") or []
        for msg in reversed(messages[-4:]):
            if not isinstance(msg, dict) or msg.get("type") != "bot":
                continue
            diag = msg.get("diagnosis") or {}
            if diag.get("render") == "sage_reco" or diag.get("recommended_medicines"):
                return True
    return False


def _has_pharmacy_location_intent(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    try:
        from src.services.counseling_triage import classify_medicine_procurement_route

        if classify_medicine_procurement_route(t):
            return True
    except ImportError:
        pass
    lower = t.lower()
    has_pharmacy = any(k in t or k in lower for k in _PHARMACY_LOCATION_KEYWORDS)
    has_location = any(h in t for h in _LOCATION_HINTS)
    if has_pharmacy and has_location:
        return True
    if "市販薬" in t and ("購入" in t or "買" in t or "どこ" in t):
        return True
    # Phase 3 (p3-store-procurement): "OTC" 表記の購入先クエリも同様に扱う（フラグ ON 時のみ）。
    try:
        from config.llm_flags import is_store_procurement_routing_enabled

        if (
            is_store_procurement_routing_enabled()
            and "otc" in lower
            and ("購入" in t or "買" in t or "どこ" in t)
        ):
            return True
    except ImportError:
        pass
    return False


def _resolve_concierge_follow_up(
    text: str,
    session: Any,
    sid: str | None,
) -> RouteDecision | None:
    try:
        from src.services.concierge_agent_history import (
            resolve_concierge_follow_up_intent,
            resolve_last_bot_message,
            resolve_prior_meta_intent,
        )
    except ImportError:
        return None

    prior = resolve_prior_meta_intent(session=session, sid=sid)
    if not prior:
        return None
    last_bot = resolve_last_bot_message((session or {}).get("messages") or [])
    follow = resolve_concierge_follow_up_intent(text, prior, last_bot=last_bot)
    if not follow:
        return None
    return RouteDecision(
        primary_route="Concierge",
        sub_route=follow,
        confidence=0.92,
        resolved_by="gate",
        source="concierge_follow_up",
    )


def _resolve_correction_route(
    text: str,
    session: Any,
    *,
    triage_result: dict[str, Any] | None = None,
) -> RouteDecision | None:
    from src.utils.input_helpers import (
        detect_correction_intent,
        has_explicit_symptom_signal,
        has_fever_signal,
    )

    if not detect_correction_intent(text):
        return None

    if session is not None and hasattr(session, "get") and session.get("pending_memory_delete"):
        from src.agents.session_agent import is_pending_delete_cancel

        if is_pending_delete_cancel(text):
            return RouteDecision(
                primary_route="SessionOps",
                sub_route="pending_clear",
                confidence=1.0,
                resolved_by="gate",
                source="correction_delete_cancel",
            )

    if has_fever_signal(text) or has_explicit_symptom_signal(text):
        sub = "fever_flow" if has_fever_signal(text) else "rule_based_recommend"
        return RouteDecision(
            primary_route="Physical",
            sub_route=sub,
            confidence=0.92,
            resolved_by="gate",
            source="correction_physical",
        )

    triage = triage_result or {}
    if str(triage.get("category") or "") == "Emergency":
        return RouteDecision(
            primary_route="Physical",
            sub_route="rule_based_recommend",
            confidence=0.85,
            resolved_by="gate",
            source="correction_emergency_downgrade",
        )

    if re.search(r"(キャンセル|やめて|消さない)", text):
        intent = None
        try:
            from src.agents.session_agent import probe_session_admin_intent

            intent = probe_session_admin_intent(text)
        except ImportError:
            pass
        if intent == "delete" or session and session.get("pending_memory_delete"):
            return RouteDecision(
                primary_route="SessionOps",
                sub_route="pending_clear",
                confidence=0.9,
                resolved_by="gate",
                source="correction_session_ops",
            )

    return None


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

    follow = _resolve_concierge_follow_up(text, session, sid)
    if follow is not None:
        return follow

    correction = _resolve_correction_route(text, session, triage_result=triage)
    if correction is not None:
        return correction

    if (
        session is not None
        and hasattr(session, "get")
        and _physical_consultation_active(session)
        and _looks_like_physical_lifestyle_followup(text)
    ):
        return RouteDecision(
            primary_route="Physical",
            sub_route="physical_lifestyle_followup",
            confidence=0.9,
            resolved_by="gate",
            source="physical_consultation_lifestyle",
        )

    if (
        session is not None
        and hasattr(session, "get")
        and isinstance(session.get("counseling_mode"), dict)
        and session.get("counseling_mode", {}).get("active")
        and not (
            _physical_consultation_active(session)
            and _looks_like_physical_lifestyle_followup(text)
        )
        and _looks_like_counseling_followup_answer(text)
    ):
        return RouteDecision(
            primary_route="Counseling",
            sub_route="counseling_continue",
            confidence=0.92,
            resolved_by="gate",
            source="counseling_pending_answer",
        )

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

    if any(h in text for h in _MEDICAL_EMERGENCY_HINTS):
        return RouteDecision(
            primary_route="Emergency",
            sub_route="medical_emergency",
            confidence=0.95,
            resolved_by="gate",
            source="medical_emergency_hint",
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

    if _has_pharmacy_location_intent(text):
        fever_active = (
            session is not None
            and hasattr(session, "get")
            and session_has_fever_context(session)
        )
        if not fever_active and not has_fever_signal(text):
            return RouteDecision(
                primary_route="Store",
                sub_route="store_locator",
                confidence=0.88,
                resolved_by="gate",
                source="pharmacy_location",
            )

    if has_explicit_symptom_signal(text):
        return RouteDecision(
            primary_route="Physical",
            sub_route="rule_based_recommend",
            confidence=0.9,
            resolved_by="gate",
            source="symptom_signal",
        )

    if (
        any(h in text for h in _EMOTIONAL_COUNSELING_HINTS)
        and not has_explicit_symptom_signal(text)
        and not has_fever_signal(text)
    ):
        return RouteDecision(
            primary_route="Counseling",
            sub_route="emotional_support",
            confidence=0.88,
            resolved_by="gate",
            source="emotional_hint",
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
