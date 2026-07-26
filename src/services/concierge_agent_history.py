"""Concierge 向け会話履歴 — 返信担当エージェントの推定と履歴整形。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_KIND_TO_AGENT: dict[str, str] = {
    "concierge_greeting": "ConciergeAgent",
    "concierge_thanks": "ConciergeAgent",
    "concierge_chitchat": "ConciergeAgent",
    "concierge_redirect": "ConciergeAgent",
    "concierge_capabilities": "ConciergeAgent",
    "concierge_architecture": "ConciergeAgent",
    "concierge_app_about": "ConciergeAgent",
    "concierge_medical_handoff": "ConciergeAgent",
    "concierge_operator": "ConciergeAgent",
    "counseling": "CounselingManager",
    "medicine_qa": "MedicineQAAgent",
    "emoji_offensive_ack": "ConciergeAgent",
    "emoji_unknown_ack": "ConciergeAgent",
}

_WHO_IS_ANSWERING_RE = re.compile(
    r"(今|いま).{0,12}(答え|回答|返信|応答).{0,12}(誰|だれ|なに|何)"
    r"|(誰|だれ).{0,12}(答え|回答|返信|応答)"
    r"|(答え|回答|返信|応答).{0,12}(誰|だれ|なに|何)"
)

_MULTI_AGENT_CONCEPT_RE = re.compile(
    r"マルチ[\s　\-]*エージェント|multi[\s\-]*agent",
    re.IGNORECASE,
)

_ARCHITECTURE_EXPLAIN_RE = re.compile(
    r"マルチ[\s　\-]*エージェント|multi[\s\-]*agent"
    r"|内部構成|エージェント.{0,8}(一覧|種類|どんな|何がある)"
    r"|(構成|役割|分担|振り分け|仕組み).{0,12}(教えて|説明|知りたい|聞きたい)"
    r"|(教えて|説明して).{0,12}(構成|役割|分担|仕組み)",
    re.IGNORECASE,
)

_AGENT_ROSTER_RE = re.compile(
    r"エージェント.{0,8}(一覧|種類|どんな|何がある|構成)"
    r"|(構成|役割|分担).{0,12}(教えて|説明|知りたい|聞きたい|は)"
    r"|(教えて|説明して).{0,12}(構成|役割|分担)"
    r"|内部構成",
    re.IGNORECASE,
)


_META_FOLLOW_UP_RE = re.compile(
    r"(詳しく|もっと|続き|深く|さらに|具体的に|もう少し)"
)

# Phase 3 (p3-concierge MR-4): 拡張フォローアップ表現（ROUTING_CONCIERGE_FOLLOWUP ON 時）
_META_FOLLOW_UP_EXTENDED_EXTRA = re.compile(
    r"(具体例|例を|について|詳細)"
)

_TOPIC_CONTINUATION_RE = re.compile(
    r"sse|cloud\s*run|rule[_\s-]?based|gcp|fastapi|postgresql|neon|gunicorn|"
    r"英語|多言語|対応言語|インフラ|api|デプロイ|マルチ|エージェント|"
    r"sage\s*terrace|otc|市販|プログラミング|スタック",
    re.IGNORECASE,
)

_PHYSICAL_SYMPTOM_RE = re.compile(
    r"頭痛|発熱|熱が|咳|腹痛|吐き気|めまい|下痢|肩こり|鼻水|喉"
)

_ARCHITECTURE_TOPIC_RE = re.compile(
    r"技術|仕組み|構成|スタック|エージェント|インフラ|デプロイ|内部|バックエンド|フロント|マルチ",
    re.IGNORECASE,
)

_DOC_FOLLOW_UP_INTENTS = frozenset({
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "doc_changelog",
})

_META_FOLLOW_UP_PRIOR_INTENTS = frozenset({
    "architecture",
    "capabilities",
    "app_about",
    "session_ops",
}) | _DOC_FOLLOW_UP_INTENTS

_FOLLOW_UP_PRIOR_EXTENDED = _META_FOLLOW_UP_PRIOR_INTENTS | frozenset({"redirect"})


def _is_concierge_followup_routing_enabled() -> bool:
    try:
        from config.llm_flags import is_concierge_followup_routing_enabled

        return is_concierge_followup_routing_enabled()
    except ImportError:
        return False


def _is_short_continuation_question(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 40:
        return False
    return bool(re.search(r"[?？]$|ですか|ますか|でしょうか", t))


def is_meta_follow_up_utterance(text: str) -> bool:
    """詳しく・もっと等のメタ会話フォローアップ表現か。"""
    t = (text or "").strip()
    if _META_FOLLOW_UP_RE.search(t):
        return True
    if _is_concierge_followup_routing_enabled():
        if _META_FOLLOW_UP_EXTENDED_EXTRA.search(t):
            return True
        if len(t) <= 40 and _TOPIC_CONTINUATION_RE.search(t):
            return True
    return False


def is_session_ops_bot_message(msg: Dict[str, Any]) -> bool:
    """直前 bot が SessionAgent / session_ops 応答か。"""
    if msg.get("session_agent") or msg.get("session_agent_kind"):
        return True
    if str(msg.get("concierge_intent") or "") == "session_ops":
        return True
    diagnosis = msg.get("diagnosis")
    if isinstance(diagnosis, dict):
        kind = str(diagnosis.get("kind") or "").strip()
        if kind.startswith("session_") or kind in ("concierge_session_ops",):
            return True
    return False


def resolve_last_bot_message(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """直近の bot メッセージ dict を返す。"""
    for msg in reversed(messages or []):
        if isinstance(msg, dict) and msg.get("type") == "bot":
            return msg
    return None


def resolve_prior_meta_intent(
    *,
    session: Any = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    sid: Optional[str] = None,
) -> Optional[str]:
    """dialogue_state / concierge_state.last_intent を優先し、無ければ履歴から返す。"""
    if session is not None:
        try:
            from src.dialogue.concierge_context import resolve_last_intent_for_session

            last = resolve_last_intent_for_session(session, sid)
            if last:
                return last
        except Exception:
            pass
    if conversation_history:
        return resolve_last_concierge_intent(conversation_history)
    return None


def should_block_structural_greeting(
    text: str,
    *,
    prior_intent: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """
    structural greeting 推定を禁止すべきか（フォローアップ regex または直前メタ意図）。
    """
    if is_meta_follow_up_utterance(text):
        return True
    block_prior = _META_FOLLOW_UP_PRIOR_INTENTS
    if _is_concierge_followup_routing_enabled():
        block_prior = _FOLLOW_UP_PRIOR_EXTENDED
    if prior_intent in block_prior:
        return True
    if conversation_history:
        hist_prior = resolve_last_concierge_intent(conversation_history)
        if hist_prior in block_prior:
            return True
    return False


def infer_lost_context_follow_up_intent(text: str) -> Optional[str]:
    """
    履歴・state 喪失時のフォローアップ推定（topic 語 + follow-up regex）。
    曖昧な場合は None（meta LLM に委ねる）。
    """
    t = (text or "").strip()
    if not t or not is_meta_follow_up_utterance(t) or len(t) > 40:
        return None
    if _ARCHITECTURE_TOPIC_RE.search(t) or len(t) <= 24:
        return "architecture"
    return None


def resolve_last_concierge_intent(messages: List[Dict[str, Any]]) -> Optional[str]:
    """直近 bot メッセージの concierge_intent を返す。"""
    for msg in reversed(messages or []):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        intent = msg.get("concierge_intent")
        if intent:
            return str(intent)
        diagnosis = msg.get("diagnosis")
        if isinstance(diagnosis, dict):
            kind = str(diagnosis.get("kind") or "").strip()
            if kind.startswith("concierge_"):
                return kind.replace("concierge_", "", 1)
    return None


def infer_prior_meta_follow_up_intent(
    text: str,
    prior_intent: Optional[str],
    *,
    last_bot: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """直前のメタ意図に続く短いフォローアップ（例: 技術面を詳しく）を推定する。"""
    t = (text or "").strip()
    if not t or not prior_intent or prior_intent not in _META_FOLLOW_UP_PRIOR_INTENTS:
        return None
    if not _META_FOLLOW_UP_RE.search(t):
        return None
    if len(t) > 40:
        return None

    try:
        from src.dialogue.routing.context_signals import (
            is_doc_changelog_continuation,
            is_explicit_new_meta_topic,
        )

        if is_explicit_new_meta_topic(t, prior_intent=prior_intent):
            return None
        if prior_intent == "doc_changelog" and not is_doc_changelog_continuation(t):
            return None
    except ImportError:
        pass

    if prior_intent == "architecture":
        if _ARCHITECTURE_TOPIC_RE.search(t) or len(t) <= 24:
            return "architecture"
        return None
    if prior_intent == "session_ops":
        if last_bot and is_session_ops_bot_message(last_bot):
            return "session_ops"
        return None
    if prior_intent in _DOC_FOLLOW_UP_INTENTS:
        return prior_intent
    if prior_intent in ("capabilities", "app_about"):
        return prior_intent
    return None


def infer_enhanced_concierge_follow_up_intent(
    text: str,
    prior_intent: Optional[str],
    *,
    last_bot: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """MR-4 拡張フォローアップ（redirect 継続・トピック継続・具体例等）。"""
    t = (text or "").strip()
    if not t or not prior_intent or prior_intent not in _FOLLOW_UP_PRIOR_EXTENDED:
        return None
    if len(t) > 40:
        return None
    if _PHYSICAL_SYMPTOM_RE.search(t):
        return None

    try:
        from src.dialogue.routing.context_signals import (
            is_doc_changelog_continuation,
            is_explicit_new_meta_topic,
        )

        if is_explicit_new_meta_topic(t, prior_intent=prior_intent):
            return None
        if prior_intent == "doc_changelog" and not is_doc_changelog_continuation(t):
            return None
    except ImportError:
        pass

    has_signal = (
        _META_FOLLOW_UP_EXTENDED_EXTRA.search(t)
        or _TOPIC_CONTINUATION_RE.search(t)
        or _is_short_continuation_question(t)
    )
    if not has_signal:
        return None

    if prior_intent == "redirect":
        return "redirect"
    if prior_intent == "architecture":
        return "architecture"
    if prior_intent == "session_ops":
        if last_bot and is_session_ops_bot_message(last_bot):
            return "session_ops"
        return None
    if prior_intent in _DOC_FOLLOW_UP_INTENTS:
        return prior_intent
    if prior_intent in ("capabilities", "app_about"):
        return prior_intent
    return None


def resolve_concierge_follow_up_intent(
    text: str,
    prior_intent: Optional[str],
    *,
    last_bot: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Gate / orchestrator 共用。基本フォローアップ後、フラグ ON 時は拡張検出。

    独立したメタ／技術質問は sticky follow-up に落とさず None を返し、
    IntentRouter / meta_triage に委ねる。
    """
    try:
        from src.dialogue.routing.context_signals import (
            is_explicit_new_meta_topic,
            looks_like_substantive_meta_question,
        )

        if is_explicit_new_meta_topic(text, prior_intent=prior_intent):
            return None
        if looks_like_substantive_meta_question(text):
            return None
    except ImportError:
        pass

    base = infer_prior_meta_follow_up_intent(text, prior_intent, last_bot=last_bot)
    if base:
        return base
    if _is_concierge_followup_routing_enabled():
        return infer_enhanced_concierge_follow_up_intent(
            text, prior_intent, last_bot=last_bot
        )
    return None


def is_who_is_answering_question(text: str) -> bool:
    return bool(_WHO_IS_ANSWERING_RE.search((text or "").strip()))


def is_multi_agent_concept_question(text: str) -> bool:
    """マルチエージェントの意味・構成を問う質問（担当者確認ではない）。"""
    t = (text or "").strip()
    if not t or is_who_is_answering_question(t):
        return False
    return bool(_MULTI_AGENT_CONCEPT_RE.search(t))


def is_architecture_explanation_question(text: str) -> bool:
    """仕組み・構成・役割分担の説明を求める質問（担当者確認ではない）。"""
    t = (text or "").strip()
    if not t or is_who_is_answering_question(t):
        return False
    return bool(_ARCHITECTURE_EXPLAIN_RE.search(t))


def is_agent_roster_question(text: str) -> bool:
    """エージェント一覧・構成・役割分担の明示的な質問。"""
    t = (text or "").strip()
    if not t or is_who_is_answering_question(t):
        return False
    return bool(_AGENT_ROSTER_RE.search(t))


def resolve_bot_responding_agent(msg: Dict[str, Any]) -> Optional[str]:
    """bot メッセージから、ユーザー向け返信の担当エージェント名を推定する。"""
    if msg.get("type") != "bot":
        return None
    if msg.get("concierge") or msg.get("concierge_intent"):
        return "ConciergeAgent"
    if msg.get("counseling") or msg.get("emotional"):
        return "CounselingManager"
    if msg.get("ask"):
        return "MedicineQAAgent"
    if msg.get("crisis_support") or msg.get("emergency_detected"):
        return "EmergencyRouter"

    diagnosis = msg.get("diagnosis")
    if isinstance(diagnosis, dict):
        kind = str(diagnosis.get("kind") or "").strip()
        if kind in _KIND_TO_AGENT:
            return _KIND_TO_AGENT[kind]
        if kind.startswith("concierge_"):
            return "ConciergeAgent"
        status = str(diagnosis.get("status") or "").strip()
        if diagnosis.get("recommended_medicines") or status in (
            "success",
            "no_candidates",
            "missing_critical_info",
        ):
            return "PhysicalOrchestrator"
        if diagnosis.get("render") == "sage_qa":
            return "MedicineQAAgent"

    return "ChatOrchestrator"


def resolve_last_responding_agent(messages: List[Dict[str, Any]]) -> Optional[str]:
    for msg in reversed(messages or []):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        if msg.get("user_info_notification"):
            continue
        agent = resolve_bot_responding_agent(msg)
        if agent:
            return agent
    return None


def format_concierge_agent_history_block(messages: List[Dict[str, Any]]) -> str:
    """会話履歴に返信担当エージェント名を付与して LLM に渡す。"""
    if not messages:
        return "（なし）"
    from src.utils.sage_message_plain import resolve_bot_user_facing_text

    lines: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("type") or "user"
        if role == "bot":
            content = resolve_bot_user_facing_text(msg)[:300]
        else:
            content = str(msg.get("content") or "").strip()[:300]
        if not content:
            continue
        if role == "bot":
            agent = resolve_bot_responding_agent(msg)
            label = f"bot[{agent}]" if agent else "bot"
            lines.append(f"{label}: {content}")
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "（なし）"
