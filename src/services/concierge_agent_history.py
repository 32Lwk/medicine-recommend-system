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
    from src.services.line_memory_context import compress_message_for_llm

    lines: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        compressed = compress_message_for_llm(msg)
        role = compressed.get("type") or "user"
        content = (compressed.get("content") or "").strip()[:300]
        if not content:
            continue
        if role == "bot":
            agent = resolve_bot_responding_agent(msg)
            label = f"bot[{agent}]" if agent else "bot"
            lines.append(f"{label}: {content}")
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "（なし）"
