"""Chat Pipeline v2 hook — Wave 1a: SessionOps + DialogueContext のみ（routing は旧 100%）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

from config.llm_flags import is_chat_pipeline_v2_for_session
from src.dialogue.envelope import ResponseEnvelope
from src.dialogue.session_ops import try_handle_session_ops

logger = logging.getLogger(__name__)

ResponseTuple = tuple[dict, int]


def v2_session_ops_enabled(sid: str | None) -> bool:
    return is_chat_pipeline_v2_for_session(sid)


def try_session_ops_route(
    session: Any,
    sid: str | None,
    user_text: str,
    client: Any,
    *,
    triage_result: dict[str, Any] | None = None,
    phase: str = "fast",
) -> Optional[ResponseTuple]:
    """v2 ON 時のみ SessionOps を実行。OFF 時は None（呼び出し元が legacy へ）。"""
    if not v2_session_ops_enabled(sid):
        return None

    logger.debug("dialogue v2 SessionOps phase=%s sid=%s", phase, sid)
    return try_handle_session_ops(
        session,
        sid,
        user_text,
        client,
        triage_result=triage_result,
    )


def wrap_session_ops_envelope(
    response: ResponseTuple,
    *,
    sid: str | None,
) -> ResponseEnvelope:
    return ResponseEnvelope.wrap_session_ops(response, sid=sid)
