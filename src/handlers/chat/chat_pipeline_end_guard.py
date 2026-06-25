"""
パイプライン終端ガード — 当該ターンで bot 応答が無い場合に redirect を補完する。

Web / LINE 共通（サーバーサイド session.messages を参照）。
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.handlers.line.line_session import count_bot_messages_in_session

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def append_redirect_bot_response(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    recommendation_client: Optional[OpenAI] = None,
) -> dict:
    """Concierge redirect テンプレートで bot メッセージを追記する。"""
    from src.agents.concierge_agent import build_concierge_payload
    from src.core.medicine_logic import client as default_client
    from src.handlers.chat.chat_concierge_route import (
        _append_bot_message,
        _mark_session_modified,
        _sync_session_db,
    )

    client = recommendation_client or default_client
    payload = build_concierge_payload("redirect", "", client, session_id=sid, history=[])
    bot = _append_bot_message(session, payload, sid)
    _mark_session_modified(session)
    if sid and client_info is not None:
        _sync_session_db(session, client_info, sid)
    logger.warning("Pipeline end guard: appended redirect bot sid=%s", sid)
    return bot


def finalize_pipeline_response(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    bot_count_before: int,
    response: ResponseTuple,
    *,
    recommendation_client: Optional[OpenAI] = None,
) -> ResponseTuple:
    """応答返却直前に bot 追記有無を確認し、無ければ redirect を補完する。"""
    if count_bot_messages_in_session(session) > bot_count_before:
        return response
    append_redirect_bot_response(session, sid, client_info, recommendation_client)
    body, status = response
    new_body = dict(body) if isinstance(body, dict) else {"status": "ok"}
    new_body["message_count"] = len(session.get("messages", []))
    new_body["pipeline_end_guard"] = "redirect"
    return new_body, status
