"""
StoreInquiryAgent — 店舗案内ハンドラのラッパ
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

ResponseTuple = Tuple[dict, int]


def handle_store_inquiry(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    sanitized_message: str,
    client: OpenAI,
    triage_result: Optional[Dict[str, Any]],
    *,
    display_user_message: str = "",
) -> Optional[ResponseTuple]:
    from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response

    return handle_store_inquiry_response(
        session,
        client_info,
        sid,
        sanitized_message,
        client,
        triage_result,
        display_user_message=display_user_message,
    )
