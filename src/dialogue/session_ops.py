"""SessionOps — 削除・要約・ステータス（Wave 1a。LINE 全機能 + Web status/summarize）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.agents.session_agent import (
    classify_session_intent,
    try_handle_session_request,
)
from src.dialogue.context import load_dialogue_context, save_dialogue_context

logger = logging.getLogger(__name__)

ResponseTuple = tuple[dict, int]


def _sync_dialogue_state(session: Any, sid: str | None) -> None:
    from src.dialogue.sync_legacy import sync_dialogue_legacy_mirrors

    sync_dialogue_legacy_mirrors(session, sid)
    ctx = load_dialogue_context(session)
    save_dialogue_context(session, ctx, dual_write=True)


def _handle_web_status(
    session: Any,
    sid: str | None,
    user_text: str,
) -> ResponseTuple:
    from src.agents.session_agent import _build_bot, _ok_response, _persist_session_messages
    from src.services.status_diagnosis_builder import build_session_integrated_status
    from src.utils.agent_trace import log_agent_step

    snapshot = dict(session) if isinstance(session, dict) else {}
    sage_diag = build_session_integrated_status(
        session_snapshot=snapshot,
        profile={},
        summaries=[],
    ).to_client_dict()
    message = str(sage_diag.get("message") or "")
    bot = _build_bot(
        session, sid, sage_diag=sage_diag, legacy_message=message, kind="status"
    )
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionOps", "web_session_status", sid=sid)
    return _ok_response(session)


def _handle_web_summarize(
    session: Any,
    sid: str | None,
    user_text: str,
    client: Any,
) -> ResponseTuple:
    from src.agents.session_agent import (
        _build_bot,
        _ok_response,
        _persist_session_messages,
        _summarize_session_llm,
    )
    from src.services.status_diagnosis_builder import build_notice_status
    from src.utils.agent_trace import log_agent_step

    summary_text = _summarize_session_llm(session, client)
    source = "session_llm"
    if not summary_text:
        summary_text = (
            "要約できる相談履歴がまだありません。"
            "症状やお薬についてお話しいただくと、ここに要約が表示されます。"
        )
        source = "empty"

    sage_diag = build_notice_status(
        summary_text,
        title="相談履歴の要約",
        kind="session_summary",
        show_feedback=True,
    ).to_client_dict()
    bot = _build_bot(
        session, sid, sage_diag=sage_diag, legacy_message=summary_text, kind="summarize"
    )
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(
        None,
        "SessionOps",
        "web_session_summarized",
        sid=sid,
        payload={"source": source},
    )
    return _ok_response(session)


def try_handle_session_ops(
    session: Any,
    sid: str | None,
    user_text: str,
    client: Any,
    *,
    triage_result: dict[str, Any] | None = None,
) -> Optional[ResponseTuple]:
    """
    SessionOps 統一入口。
    LINE: delete / summarize / status（SessionAgent 委譲）
    Web: status / summarize のみ（delete は None → 通常ルート）
    """
    _sync_dialogue_state(session, sid)

    from src.services.line_user_memory import is_line_memory_session

    if is_line_memory_session(sid, session):
        resp = try_handle_session_request(
            session,
            sid,
            user_text,
            client,
            triage_result=triage_result,
        )
        if resp is not None:
            _sync_dialogue_state(session, sid)
        return resp

    intent = classify_session_intent(user_text, triage_result=triage_result)
    if intent == "delete":
        return None
    if intent == "status":
        resp = _handle_web_status(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    if intent == "summarize":
        resp = _handle_web_summarize(session, sid, user_text, client)
        _sync_dialogue_state(session, sid)
        return resp
    return None
