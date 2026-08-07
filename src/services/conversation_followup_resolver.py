"""
曖昧フォローアップの文脈・意図解決。

ルールベース gate が inconclusive なときのみ LLM を呼び、
特定フレーズへの過学習ではなく会話全体からユーザー意図を判定する。
"""
from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

_AMBIGUOUS_MAX_CHARS = 120
_SESSION_CACHE_KEY = "_followup_intent_cache"


class FollowupIntent(str, Enum):
    RESCORE = "rescore"
    MEDICINE_QA = "medicine_qa"
    TRAVEL = "travel"
    CONCIERGE = "concierge"
    CONTINUE_THREAD = "continue_thread"
    NONE = "none"


def _has_prior_medicine_context(
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> bool:
    if recommended_medicines:
        return True
    for msg in (conversation_history or [])[-12:]:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("type") or "").lower() == "bot":
            diag = msg.get("diagnosis") or {}
            if diag.get("recommended_medicines") or diag.get("kind") in (
                "recommendation",
                "medicine_qa",
                "sage_reco",
            ):
                return True
    return False


def should_invoke_ambiguous_resolver(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """ルール不足時に LLM 文脈判定を試みるべきか。"""
    t = (text or "").strip()
    if not t or len(t) > _AMBIGUOUS_MAX_CHARS:
        return False
    if not _has_prior_medicine_context(
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return False
    try:
        from src.services.concierge_intent import classify_concierge_intent

        if classify_concierge_intent(t) in ("greeting", "thanks", "chitchat"):
            return False
    except ImportError:
        pass
    return True


def _format_recent_turns(
    conversation_history: list[dict[str, Any]] | None,
    *,
    max_turns: int = 6,
) -> str:
    try:
        from src.services.medicine_thread_context import format_recent_turns_plain

        return format_recent_turns_plain(conversation_history, max_turns=max_turns)
    except ImportError:
        lines: list[str] = []
        for msg in (conversation_history or [])[-max_turns * 2 :]:
            if not isinstance(msg, dict):
                continue
            role = "ユーザー" if str(msg.get("type") or msg.get("role")) == "user" else "AI"
            content = str(msg.get("content") or msg.get("message") or "")[:350]
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)


def _parse_intent_response(raw: str) -> FollowupIntent | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(obj, dict):
        return None
    intent = str(obj.get("user_intent") or obj.get("intent") or "").strip().lower()
    mapping = {
        "rescore": FollowupIntent.RESCORE,
        "physical": FollowupIntent.RESCORE,
        "symptom_change": FollowupIntent.RESCORE,
        "new_symptom": FollowupIntent.RESCORE,
        "medicine_qa": FollowupIntent.MEDICINE_QA,
        "qa": FollowupIntent.MEDICINE_QA,
        "followup_qa": FollowupIntent.MEDICINE_QA,
        "travel": FollowupIntent.TRAVEL,
        "travel_qa": FollowupIntent.TRAVEL,
        "concierge": FollowupIntent.CONCIERGE,
        "meta": FollowupIntent.CONCIERGE,
        "continue": FollowupIntent.CONTINUE_THREAD,
        "continue_thread": FollowupIntent.CONTINUE_THREAD,
        "none": FollowupIntent.NONE,
        "summary_ok": FollowupIntent.NONE,
    }
    return mapping.get(intent)


def resolve_ambiguous_followup_intent(
    text: str,
    *,
    session: Any = None,
    sid: Optional[str] = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    client: Any = None,
) -> FollowupIntent | None:
    """
    曖昧フォローアップのユーザー意図を LLM で解決。
    ルール gate の補助。失敗時は None（呼び出し元が従来挙動）。
    """
    t = (text or "").strip()
    if not should_invoke_ambiguous_resolver(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return None

    cache_key = f"{sid or 'nosid'}:{hash(t)}"
    if session and isinstance(session, dict):
        cache = session.setdefault(_SESSION_CACHE_KEY, {})
        if cache_key in cache:
            cached = cache[cache_key]
            try:
                return FollowupIntent(cached)
            except ValueError:
                pass

    try:
        from config.llm_flags import is_routing_followup_llm_enabled
    except ImportError:
        return None
    if not is_routing_followup_llm_enabled(sid):
        return None

    if client is None:
        try:
            from src.core.llm_client import get_openai_client

            client = get_openai_client()
        except Exception:
            client = None
    if client is None:
        return None

    product_names = ", ".join(
        str(m.get("product_name") or m.get("name") or "")
        for m in (recommended_medicines or [])[:5]
        if m.get("product_name") or m.get("name")
    )
    recent = _format_recent_turns(conversation_history)
    prompt = (
        "あなたは市販薬相談チャットの文脈分類器です。"
        "特定キーワード一致ではなく、会話全体からユーザーの意図を判定してください。\n\n"
        "【分類】\n"
        "- rescore: 主訴・症状の追加・訂正・悪化で新しい市販薬推奨が必要\n"
        "- medicine_qa: 既に出た推奨薬についての質問（用法・併用・比較・指示語）\n"
        "- travel: 旅行・海外持ち込み・空港・書類の続き\n"
        "- continue_thread: 医薬品スレッドの短い確認・感想（再推奨不要）\n"
        "- concierge: 挨拶・雑談・アプリ仕組み等（医薬品相談外）\n"
        "- none: 要約で足りる単純確認\n\n"
        f"ユーザー発話: {t}\n"
        f"直近推奨薬: {product_names or '(なし)'}\n"
        f"直近会話:\n{recent or '(なし)'}\n\n"
        'JSON のみ: {"user_intent": "rescore|medicine_qa|travel|continue_thread|concierge|none", '
        '"reason": "短い理由"}'
    )
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text

        resp = chat_completion_create(
            client,
            model_role="router",
            path="conversation/followup_intent",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        raw = extract_completion_text(resp)
        intent = _parse_intent_response(raw or "")
        if intent and session and isinstance(session, dict):
            session.setdefault(_SESSION_CACHE_KEY, {})[cache_key] = intent.value
        return intent
    except Exception:
        logger.debug("ambiguous followup intent LLM failed", exc_info=True)
        return None


def followup_intent_warrants_rescore(intent: FollowupIntent | None) -> bool:
    return intent in (FollowupIntent.RESCORE, FollowupIntent.TRAVEL)


def followup_intent_warrants_medicine_qa(intent: FollowupIntent | None) -> bool:
    return intent in (
        FollowupIntent.MEDICINE_QA,
        FollowupIntent.CONTINUE_THREAD,
        FollowupIntent.TRAVEL,
    )
