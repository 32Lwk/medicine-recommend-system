"""
挨拶の早期応答 — ConciergeAgent へ委譲（後方互換ラッパ）
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.core.medicine_logic import client as openai_client

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def try_greeting_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    *,
    triage_result: Optional[dict] = None,
    recommendation_client: Optional[OpenAI] = None,
) -> Optional[ResponseTuple]:
    """
    純粋な挨拶なら ConciergeAgent で応答。該当しなければ None。
  """
    from src.handlers.chat.chat_concierge_route import try_concierge_response

    return try_concierge_response(
        session,
        client_info,
        sid,
        user_message,
        user_message,
        triage_result,
        recommendation_client or openai_client,
    )
