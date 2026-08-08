"""
ChatOrchestrator — Other カテゴリ向け Concierge メタ意図の付与（LLM 分類）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from src.services.concierge_intent import ConciergeIntent, classify_concierge_intent

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
    "doc_changelog",
    "chitchat",
    "greeting",
    "redirect",
})


def _apply_follow_up_intent(
    out: Dict[str, Any],
    text: str,
    follow: str,
    *,
    source: str,
    last_bot: Optional[Dict[str, Any]] = None,
    triage_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    out["concierge_intent"] = follow
    out["concierge_intent_source"] = source
    if follow == "session_ops":
        from src.agents.session_agent import classify_session_intent

        session_intent = classify_session_intent(text, triage_result=triage_result or out)
        if session_intent == "none" and last_bot:
            kind = str(last_bot.get("session_agent_kind") or "").strip()
            if kind in ("delete", "summarize", "status"):
                session_intent = kind  # type: ignore[assignment]
        if session_intent != "none":
            out["session_intent"] = session_intent
    logger.info("🛎️ ConciergeOrchestrator: prior intent follow-up intent=%s", follow)
    return out


def enrich_other_concierge_intent(
    triage_result: Dict[str, Any],
    user_text: str,
    client: OpenAI,
    *,
    conversation_history: Optional[list] = None,
    session_id: Optional[str] = None,
    session: Any = None,
    alt_texts: Optional[list] = None,
    routing_ctx: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Other トリアージ結果に concierge_intent を付与する（オーケストレーター段階）。
    挨拶・感謝・雑談は軽量分類、メタ質問は meta_triage LLM。
    """
    out = dict(triage_result or {})
    if out.get("category") != "Other":
        return out

    text = (user_text or "").strip()
    if not text:
        return out

    from src.services.routing_context import evaluate_store_gate

    store_probable = evaluate_store_gate(
        text,
        *(alt_texts or []),
        triage_result=out,
        routing_ctx=routing_ctx,
    )
    if store_probable:
        out.pop("concierge_intent", None)
        out.pop("concierge_intent_source", None)
        return out

    from config.llm_flags import is_intent_router_primary_enabled

    if out.get("_intent_router_dispatch") and is_intent_router_primary_enabled(session_id):
        pre = out.get("concierge_intent")
        if pre in _VALID_CONCIERGE_INTENTS:
            logger.info(
                "🛎️ ConciergeOrchestrator: PRIMARY locked, skip meta_triage intent=%s",
                pre,
            )
            return out
        if pre:
            out["concierge_intent"] = _resolve_router_dispatched_concierge_intent(pre, text)
            out["concierge_intent_source"] = "router_primary_resolve"
            logger.info(
                "🛎️ ConciergeOrchestrator: PRIMARY resolve without meta_triage intent=%s",
                out["concierge_intent"],
            )
            return out

    sub = str((out or {}).get("subcategory") or "").lower()
    try:
        triage_conf = float((out or {}).get("confidence", 0))
    except (TypeError, ValueError):
        triage_conf = 0.0
    if sub == "session_admin" and triage_conf >= 0.85:
        from src.agents.session_agent import classify_session_intent

        out["concierge_intent"] = "session_ops"
        out["concierge_intent_source"] = "triage_session_admin"
        out["session_intent"] = classify_session_intent(text, triage_result=out)
        logger.info(
            "🛎️ ConciergeOrchestrator: triage session_admin intent=%s (meta skipped)",
            out["session_intent"],
        )
        return out

    from src.services.concierge_intent import _is_medicine_consultation

    prior_intent: Optional[str] = None
    last_bot = None
    if not _is_medicine_consultation(text):
        from src.services.concierge_agent_history import (
            infer_lost_context_follow_up_intent,
            resolve_concierge_follow_up_intent,
            resolve_last_bot_message,
            resolve_prior_meta_intent,
        )

        prior_intent = resolve_prior_meta_intent(
            session=session,
            conversation_history=conversation_history,
            sid=session_id,
        )
        last_bot = resolve_last_bot_message(conversation_history or [])
        follow = resolve_concierge_follow_up_intent(text, prior_intent, last_bot=last_bot)
        if follow:
            return _apply_follow_up_intent(
                out,
                text,
                follow,
                source="prior_intent_follow_up",
                last_bot=last_bot,
                triage_result=out,
            )

        from src.services.concierge_intent import probe_meta_concierge_intent

        probed_direct = probe_meta_concierge_intent(text)
        if probed_direct and not _is_medicine_consultation(text):
            out["concierge_intent"] = probed_direct
            out["concierge_intent_source"] = "keyword_probe"
            logger.info("🛎️ ConciergeOrchestrator: keyword_probe intent=%s", probed_direct)
            return out

        lost = infer_lost_context_follow_up_intent(text)
        if lost:
            return _apply_follow_up_intent(
                out,
                text,
                lost,
                source="lost_context_follow_up",
                triage_result=out,
            )

    from src.services.concierge_intent import probe_session_admin_intent

    probed_session = probe_session_admin_intent(text)
    if probed_session:
        out["session_intent"] = probed_session
        out["concierge_intent"] = "session_ops"
        out["concierge_intent_source"] = "session_keyword_probe"
        logger.info("🛎️ ConciergeOrchestrator: session_intent=%s (probe)", probed_session)
        return out

    if out.get("concierge_intent") in _VALID_CONCIERGE_INTENTS:
        return out

    fast = classify_concierge_intent(text)
    if fast in ("greeting", "thanks"):
        out["concierge_intent"] = fast
        out["concierge_intent_source"] = "exact_match_gate"
        logger.info("🛎️ ConciergeOrchestrator: exact_match intent=%s", fast)
        return out

    from src.services.concierge_intent import probe_meta_concierge_intent

    from src.services.concierge_intent import _is_medicine_consultation

    probed = probe_meta_concierge_intent(text)
    if probed and not _is_medicine_consultation(text):
        out["concierge_intent"] = probed
        out["concierge_intent_source"] = "keyword_probe"
        logger.info("🛎️ ConciergeOrchestrator: keyword_probe intent=%s", probed)
        return out
    if probed and _is_medicine_consultation(text):
        logger.info(
            "🛎️ ConciergeOrchestrator: keyword_probe %s + medicine hint → meta LLM",
            probed,
        )

    from src.services.meta_triage import (
        classify_meta_concierge_intent,
        should_skip_meta_triage_llm,
    )

    if should_skip_meta_triage_llm(
        out,
        text,
        store_probable=store_probable,
        prior_meta_intent=prior_intent,
        conversation_history=conversation_history,
    ):
        from src.services.concierge_intent import infer_structural_concierge_intent

        structural = infer_structural_concierge_intent(
            text,
            prior_meta_intent=prior_intent,
            conversation_history=conversation_history,
            session=session,
            sid=session_id,
        )
        if structural:
            out["concierge_intent"] = structural
            out["concierge_intent_source"] = "structural_greeting"
            logger.info(
                "🛎️ ConciergeOrchestrator: meta LLM skipped, structural intent=%s",
                structural,
            )
        else:
            out["concierge_intent"] = "redirect"
            out["concierge_intent_source"] = "general_other_fallback"
            logger.info(
                "🛎️ ConciergeOrchestrator: meta LLM skipped (general_other high conf), "
                "fallback intent=redirect"
            )
        return out

    from src.services.pipeline_perf import mark_pipeline_step

    mark_pipeline_step("meta_triage_start")
    meta = classify_meta_concierge_intent(
        text,
        client,
        conversation_history=conversation_history,
    )
    mark_pipeline_step("meta_triage_end")

    if meta in ("redirect", "chitchat") and evaluate_store_gate(
        text,
        *(alt_texts or []),
        triage_result=out,
        routing_ctx=routing_ctx,
    ):
        logger.info(
            "🛎️ ConciergeOrchestrator: store inquiry, ignore meta intent=%s",
            meta,
        )
        return out
    if meta == "session_ops":
        from src.agents.session_agent import classify_session_intent

        out["concierge_intent"] = "session_ops"
        out["concierge_intent_source"] = "meta_triage"
        out["session_intent"] = classify_session_intent(text, triage_result=out)
        logger.info("🛎️ ConciergeOrchestrator: meta session_ops intent=%s", out["session_intent"])
        return out
    if meta:
        out["concierge_intent"] = meta
        out["concierge_intent_source"] = "meta_triage"
        logger.info("🛎️ ConciergeOrchestrator: meta intent=%s", meta)
        if meta not in ("chitchat", "redirect", "none"):
            _verify_meta_async(
                user_text=text,
                intent=meta,
                client=client,
                session_id=session_id,
            )
    else:
        logger.info("🛎️ ConciergeOrchestrator: meta intent unresolved (none)")
        out["concierge_intent"] = "redirect"
        out["concierge_intent_source"] = "meta_unresolved_fallback"
    return out


def resolve_intent_from_triage(
    triage_result: Optional[Dict[str, Any]],
    session: Any,
    user_text: str,
    *,
    sid: Optional[str] = None,
    routing_ctx: Optional[Any] = None,
    alt_texts: Optional[list] = None,
    conversation_history: Optional[list] = None,
) -> Optional[ConciergeIntent]:
    """triage_result.concierge_intent を優先し、雑談連続時のみ redirect に昇格。"""
    from src.services.routing_context import evaluate_store_gate

    triage = triage_result or {}
    from src.services.contact_channel_intent import (
        classify_contact_channel_question,
        contact_channel_to_concierge_intent,
    )

    channel = classify_contact_channel_question(user_text, history=conversation_history)
    if channel:
        mapped = contact_channel_to_concierge_intent(channel)
        if mapped:
            return mapped  # type: ignore[return-value]

    router_dispatch = bool(triage.get("_intent_router_dispatch"))
    if not router_dispatch and evaluate_store_gate(
        user_text,
        *(alt_texts or []),
        triage_result=triage,
        routing_ctx=routing_ctx,
    ):
        return None

    pre = triage.get("concierge_intent")
    if pre not in _VALID_CONCIERGE_INTENTS:
        if router_dispatch and pre:
            return _resolve_router_dispatched_concierge_intent(pre, user_text)
        return None

    if pre == "chitchat":
        from src.dialogue.concierge_context import resolve_off_topic_turns

        if resolve_off_topic_turns(session, sid) >= 2:
            return "redirect"
    return pre  # type: ignore[return-value]


def _resolve_router_dispatched_concierge_intent(
    pre: str,
    user_text: str,
) -> ConciergeIntent:
    """IntentRouter が Concierge を確定したが triage intent が未登録のときの解決。"""
    from src.services.concierge_intent import (
        classify_concierge_intent,
        infer_structural_concierge_intent,
        probe_meta_concierge_intent,
    )

    for resolver in (
        classify_concierge_intent,
        probe_meta_concierge_intent,
        infer_structural_concierge_intent,
    ):
        hit = resolver(user_text)
        if hit in _VALID_CONCIERGE_INTENTS:
            return hit  # type: ignore[return-value]
    if pre == "general_other":
        logger.info(
            "🛎️ ConciergeOrchestrator: router dispatch general_other → redirect fallback"
        )
        return "redirect"
    logger.info(
        "🛎️ ConciergeOrchestrator: router dispatch unknown intent=%s → redirect",
        pre,
    )
    return "redirect"


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
