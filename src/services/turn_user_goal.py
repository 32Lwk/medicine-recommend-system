"""ターン単位 user_goal 解決 — routing 前の軽量意図分類（ルール優先、必要時 LLM）。"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

UserGoal = str  # answer | clarify | pivot | acknowledge | continue_thread | correction | session_ops

_CORRECTION_RE = re.compile(r"違う|いや|ちがう|そうじゃ|それじゃ")
_CLARIFY_NEEDED_RE = re.compile(r"飲み合わせ|併用|一緒に|他の薬")
_SESSION_OPS_RE = re.compile(r"削除|消して|履歴|要約|ステータス|この会話")
_PIVOT_META_RE = re.compile(r"技術|スタック|アーキテクチャ|API|インフラ|プライバシー|利用規約")
_ACK_RE = re.compile(r"^(ありがとう|了解|なるほど|そうですね|うん)[!！。.\s]*$")


def resolve_turn_user_goal(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    active_products: list[str] | None = None,
    client: Any = None,
    use_llm: bool = False,
) -> UserGoal:
    """今ターンのユーザー goal を返す。routing / trace / judge で共有。"""
    t = (text or "").strip()
    if not t:
        return "acknowledge"

    if _SESSION_OPS_RE.search(t):
        return "session_ops"

    if _CORRECTION_RE.search(t):
        return "correction"

    if _PIVOT_META_RE.search(t) and active_products:
        return "pivot"

    if _ACK_RE.match(t):
        return "acknowledge"

    if _CLARIFY_NEEDED_RE.search(t) and not active_products:
        try:
            from src.dialogue.routing.context_signals import extract_drug_entities

            if not extract_drug_entities(t):
                return "clarify"
        except Exception:
            return "clarify"

    if active_products or (conversation_history and len(conversation_history) > 2):
        if re.search(r"^[それこのあの]", t) or len(t) <= 24:
            return "continue_thread"

    if "?" in t or "？" in t or re.search(r"教えて|ですか|でしょうか", t):
        return "answer"

    if use_llm and client is not None:
        return _resolve_turn_user_goal_llm(t, conversation_history, client)

    return "answer"


def _resolve_turn_user_goal_llm(
    text: str,
    conversation_history: list[dict[str, Any]] | None,
    client: Any,
) -> UserGoal:
    try:
        from src.core.llm_client import chat_completion_create

        hist = ""
        for msg in (conversation_history or [])[-4:]:
            role = msg.get("role") or msg.get("type") or "?"
            content = str(msg.get("content") or "")[:120]
            hist += f"{role}: {content}\n"

        prompt = f"""会話履歴:
{hist or "（なし）"}

当ターン user: {text}

今ターンの user_goal を1語だけ: answer|clarify|pivot|acknowledge|continue_thread|correction|session_ops
JSON: {{"user_goal":"..."}}"""

        resp = chat_completion_create(
            client,
            model_role="concierge_eval",
            path="turn_user_goal",
            messages=[
                {"role": "system", "content": "JSON のみ"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=40,
            temperature=0.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        import json

        if "{" in raw:
            raw = raw[raw.find("{") : raw.rfind("}") + 1]
        parsed = json.loads(raw)
        goal = str(parsed.get("user_goal") or "answer")
        if goal in (
            "answer",
            "clarify",
            "pivot",
            "acknowledge",
            "continue_thread",
            "correction",
            "session_ops",
        ):
            return goal
    except Exception:
        logger.debug("turn_user_goal LLM skipped", exc_info=True)
    return "answer"
