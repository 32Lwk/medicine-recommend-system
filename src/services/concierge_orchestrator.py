"""
ChatOrchestrator — Other カテゴリ向け Concierge メタ意図の付与（LLM 分類）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from src.services.concierge_intent import ConciergeIntent, classify_concierge_intent
from src.services.concierge_keyword_probe import probe_concierge_keyword_candidates
from src.services.routing_keyword_policy import attach_routing_keyword_candidates

logger = logging.getLogger(__name__)

_VALID_CONCIERGE_INTENTS = frozenset({
    "greeting",
    "thanks",
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "chitchat",
    "redirect",
})


def enrich_other_concierge_intent(
    triage_result: Dict[str, Any],
    user_text: str,
    client: OpenAI,
    *,
    conversation_history: Optional[list] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Other トリアージ結果に concierge_intent を付与する（オーケストレーター段階）。
    挨拶・感謝・雑談は軽量分類、メタ質問は meta_triage LLM。
    """
    out = dict(triage_result or {})
    if out.get("category") != "Other":
        return out
    if out.get("concierge_intent") in _VALID_CONCIERGE_INTENTS:
        return out

    text = (user_text or "").strip()
    if not text:
        return out

    chitchat_candidates = probe_concierge_keyword_candidates(text)
    if chitchat_candidates:
        out = attach_routing_keyword_candidates(out, chitchat_candidates, source="concierge_probe")

    fast = classify_concierge_intent(text)
    if fast in ("greeting", "thanks"):
        out["concierge_intent"] = fast
        out["concierge_intent_source"] = "exact_match_gate"
        logger.info("🛎️ ConciergeOrchestrator: exact_match intent=%s", fast)
        return out

    from src.services.meta_triage import classify_meta_concierge_intent

    meta = classify_meta_concierge_intent(
        text,
        client,
        conversation_history=conversation_history,
    )
    if meta:
        out["concierge_intent"] = meta
        out["concierge_intent_source"] = "meta_triage"
        logger.info("🛎️ ConciergeOrchestrator: meta intent=%s", meta)
        _verify_meta_async(
            user_text=text,
            intent=meta,
            client=client,
            session_id=session_id,
        )
    else:
        logger.info("🛎️ ConciergeOrchestrator: meta intent unresolved (none)")
    return out


def resolve_intent_from_triage(
    triage_result: Optional[Dict[str, Any]],
    session: Any,
    user_text: str,
) -> Optional[ConciergeIntent]:
    """triage_result.concierge_intent を優先し、雑談連続時のみ redirect に昇格。"""
    triage = triage_result or {}
    pre = triage.get("concierge_intent")
    if pre not in _VALID_CONCIERGE_INTENTS:
        return None

    if pre == "chitchat":
        from src.agents.concierge_agent import get_concierge_state

        state = get_concierge_state(session)
        if int(state.get("off_topic_turns") or 0) >= 2:
            return "redirect"
    return pre  # type: ignore[return-value]


def _verify_meta_async(
    *,
    user_text: str,
    intent: str,
    client: OpenAI,
    session_id: Optional[str],
) -> None:
    try:
        from src.services.routing_validator import verify_routing_async

        verify_routing_async(
            route_kind="concierge_meta",
            user_text=user_text,
            decided_category=intent,
            client=client,
            session_id=session_id,
            extra={"concierge_intent": intent},
        )
    except Exception:
        pass
