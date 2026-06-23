"""
ChatPipeline — トリアージ後のエージェント経路（LLM_AGENT_ENABLED 時）

既存 chat_handler の巨大分岐を段階的に委譲する薄型オーケストレータ。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from config.llm_flags import is_agent_enabled
from src.agents.protocols import HandoffResult
from src.agents.triage_agent import resolve_handoff, run_triage_agent

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


@dataclass
class PipelineResult:
    handled: bool
    response: Optional[ResponseTuple] = None
    triage_result: Optional[Dict[str, Any]] = None
    handoff: Optional[HandoffResult] = None


class ChatPipeline:
    """ハイブリッドオーケストレーション（コード優先・LLMは振り分けのみ）"""

    def __init__(self, client: OpenAI):
        self._client = client

    def run_triage(
        self,
        user_message: str,
        *,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return run_triage_agent(user_message, self._client, user_info=user_info)

    def after_triage(
        self,
        session: Any,
        client_info: Any,
        sid: Optional[str],
        user_message: str,
        sanitized_message: str,
        triage_result: Dict[str, Any],
        monitor: Any,
    ) -> PipelineResult:
        handoff = resolve_handoff(triage_result, sanitized_message, session.get("user_attributes"))
        session["agent_handoff"] = handoff.target
        session["agent_handoff_payload"] = handoff.payload
        session.modified = True

        category = triage_result.get("category", "Other")
        confidence = float(triage_result.get("confidence") or 1.0)

        if handoff.stop or category == "Emergency":
            return PipelineResult(handled=False, triage_result=triage_result, handoff=handoff)

        if category == "Emotional" and confidence >= 0.5:
            from src.handlers.chat.chat_emotional_route import (
                detect_insomnia_keyword,
                detect_sleepiness_keyword,
                handle_emotional_category,
            )

            emo_resp = handle_emotional_category(
                session,
                sid,
                user_message,
                sanitized_message,
                triage_result,
                self._client,
                has_sleepiness_keyword=session.get("has_sleepiness_keyword")
                or detect_sleepiness_keyword(sanitized_message),
                has_insomnia_keyword=detect_insomnia_keyword(sanitized_message),
            )
            if emo_resp:
                return PipelineResult(
                    handled=True, response=emo_resp, triage_result=triage_result, handoff=handoff
                )

        if category == "Physical":
            from src.agents.physical_orchestrator import run_physical_recommendation

            rb = run_physical_recommendation(
                sanitized_message,
                user_info=session.get("user_attributes"),
                client=self._client,
                session_id=sid,
            )
            session["agent_rule_based_preview"] = {
                "names": rb.get("recommended_medicine_names", []),
                "algorithm": rb.get("algorithm"),
            }
            session.modified = True
            return PipelineResult(handled=False, triage_result=triage_result, handoff=handoff)

        return PipelineResult(handled=False, triage_result=triage_result, handoff=handoff)


def try_agent_pipeline(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Optional[Dict[str, Any]],
    recommendation_client: OpenAI,
    monitor: Any,
) -> Optional[ResponseTuple]:
    """非推奨: ChatOrchestrator へ委譲。新規コードは try_orchestrator_route を使用。"""
    import warnings

    warnings.warn(
        "try_agent_pipeline is deprecated; use try_orchestrator_route",
        DeprecationWarning,
        stacklevel=2,
    )
    if not is_agent_enabled() or not triage_result:
        return None
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import try_orchestrator_route

    ctx = ChatPostContext(
        session=session,
        client_info=client_info,
        sid=sid,
        monitor=monitor,
        user_agent=getattr(client_info, "user_agent", ""),
        client_ip=getattr(client_info, "client_ip", ""),
        user_message=user_message,
        sanitized_message=sanitized_message,
        processed_message=sanitized_message,
        triage_result=triage_result,
        recommendation_client=recommendation_client,
    )
    return try_orchestrator_route(ctx, monitor)
