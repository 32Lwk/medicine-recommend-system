"""Layer 3 — 曖昧フォローアップの LLM 再判定（オフライン rule fallback 付き）。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from src.dialogue.routing.context_signals import (
    ContextFeatures,
    is_doc_changelog_continuation,
    is_explicit_new_meta_topic,
)
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)

_VALID_CONCIERGE_SUB_ROUTES = frozenset({
    "app_about",
    "architecture",
    "capabilities",
    "doc_changelog",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "redirect",
    "session_ops",
    "greeting",
    "thanks",
    "chitchat",
})


def _rule_based_follow_up(
    text: str,
    features: ContextFeatures,
) -> RouteDecision | None:
    """LLM 不可時の決定論フォールバック。"""
    prior = features.prior_route or features.prior_concierge_intent
    if not prior or not features.is_ambiguous_short_follow_up:
        return None

    if is_explicit_new_meta_topic(text, prior_intent=prior):
        if _APP_ABOUT_IN_TEXT(text):
            return RouteDecision(
                primary_route="Concierge",
                sub_route="app_about",
                confidence=0.88,
                resolved_by="gate",
                source="follow_up_rule_topic_break",
            )
        return RouteDecision(
            primary_route="Concierge",
            sub_route="architecture",
            confidence=0.86,
            resolved_by="gate",
            source="follow_up_rule_topic_break",
        )

    if prior == "doc_changelog" and is_doc_changelog_continuation(text):
        return RouteDecision(
            primary_route="Concierge",
            sub_route="doc_changelog",
            confidence=0.9,
            resolved_by="gate",
            source="follow_up_rule_changelog_continue",
        )

    if prior in ("app_about", "capabilities", "architecture") and len(text) <= 24:
        return RouteDecision(
            primary_route="Concierge",
            sub_route=prior,
            confidence=0.87,
            resolved_by="gate",
            source="follow_up_rule_meta_continue",
        )
    return None


_APP_ABOUT_IN_TEXT = lambda t: bool(  # noqa: E731
    re.search(
        r"あなた|サービス|アプリ|Sage\s*Terrace|何が(?:できる|出来る)",
        t or "",
        re.IGNORECASE,
    )
)


def _build_follow_up_prompt(
    text: str,
    features: ContextFeatures,
    *,
    last_bot_summary: str = "",
    recent_turns: str = "",
) -> str:
    return (
        "あなたはチャットボットのルーティング判定器です。"
        "ユーザーの短いフォローアップ発話が、直前トピックの継続か新トピックかを判定してください。\n\n"
        f"ユーザー発話: {text}\n"
        f"直前ボットカード種別: {features.last_bot_card_type or 'unknown'}\n"
        f"直前 Concierge intent: {features.prior_concierge_intent or features.prior_route or 'unknown'}\n"
        f"直前ボット要約: {last_bot_summary or '(なし)'}\n"
        f"直近会話:\n{recent_turns or '(なし)'}\n\n"
        "JSON のみで返答:\n"
        '{"is_same_topic_continuation": true/false, '
        '"recommended_sub_route": "app_about|architecture|doc_changelog|capabilities|...", '
        '"reason": "短い理由"}'
    )


def _parse_follow_up_response(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


def resolve_follow_up_route(
    user_text: str,
    features: ContextFeatures,
    *,
    session: Any = None,
    client: Any = None,
    last_bot_summary: str = "",
    recent_turns: str = "",
) -> RouteDecision | None:
    """曖昧短文フォローアップの route を解決。LLM → rule fallback。"""
    text = (user_text or "").strip()
    if not text or not features.is_ambiguous_short_follow_up:
        return None

    try:
        from config.llm_flags import is_routing_followup_llm_enabled

        llm_enabled = is_routing_followup_llm_enabled()
    except ImportError:
        llm_enabled = False

    if llm_enabled and client is not None:
        try:
            from src.core.llm_client import chat_completion_create

            prompt = _build_follow_up_prompt(
                text,
                features,
                last_bot_summary=last_bot_summary,
                recent_turns=recent_turns,
            )
            resp = chat_completion_create(
                client,
                messages=[{"role": "user", "content": prompt}],
                model=None,
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            raw = (resp.choices[0].message.content or "").strip()
            parsed = _parse_follow_up_response(raw)
            if parsed:
                sub = str(parsed.get("recommended_sub_route") or "").strip()
                if sub in _VALID_CONCIERGE_SUB_ROUTES:
                    return RouteDecision(
                        primary_route="Concierge",
                        sub_route=sub,
                        confidence=0.91,
                        resolved_by="llm",
                        source="follow_up_llm",
                        meta={
                            "is_same_topic_continuation": parsed.get("is_same_topic_continuation"),
                            "reason": parsed.get("reason"),
                        },
                    )
        except Exception:
            logger.debug("follow_up_llm failed, falling back to rules", exc_info=True)

    return _rule_based_follow_up(text, features)
