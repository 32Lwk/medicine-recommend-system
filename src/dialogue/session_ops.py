"""SessionOps — 削除・要約・ステータス（Wave 1a。LINE 全機能 + Web status/summarize）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.agents.session_agent import (
    classify_session_intent,
    classify_session_ops_detail,
    is_pending_delete_cancel,
    try_handle_session_request,
)
from src.dialogue.context import load_dialogue_context, save_dialogue_context

logger = logging.getLogger(__name__)

ResponseTuple = tuple[dict, int]

_DELETE_CONFIRM_BOT_KINDS = frozenset(
    {
        "memory_delete_confirm",
        "delete_confirm",
        "memory_delete_pending",
        "delete_pending",
        "memory_delete_explain",
        "delete_explain",
    }
)
_DELETE_CONFIRM_AGENT_KINDS = frozenset({"delete_confirm", "delete_pending", "delete_explain"})


def _pending_delete_from_dialogue_state(session: Any) -> dict[str, Any] | None:
    ctx = session.get("dialogue_state")
    if not isinstance(ctx, dict):
        return None
    pending = (ctx.get("pending") or {}).get("session_delete")
    return pending if isinstance(pending, dict) else None


def _last_bot_awaiting_delete_confirmation(session: Any) -> bool:
    messages = session.get("messages") or []
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        diag = msg.get("diagnosis")
        if isinstance(diag, dict):
            kind = str(diag.get("kind") or "").strip()
            if kind in _DELETE_CONFIRM_BOT_KINDS:
                return True
        agent_kind = str(msg.get("session_agent_kind") or "").strip()
        if agent_kind in _DELETE_CONFIRM_AGENT_KINDS:
            return True
        return False
    return False


def is_awaiting_memory_delete_confirmation(
    session: Any,
    *,
    allow_bot_confirm_fallback: bool = False,
) -> bool:
    if session.get("pending_memory_delete"):
        return True
    if _pending_delete_from_dialogue_state(session):
        return True
    if allow_bot_confirm_fallback and _last_bot_awaiting_delete_confirmation(session):
        return True
    return False


def _ensure_legacy_pending_for_delete(session: Any, sid: str | None) -> None:
    if session.get("pending_memory_delete"):
        return
    dlg = _pending_delete_from_dialogue_state(session)
    session["pending_memory_delete"] = {
        "scope": (dlg or {}).get("scope") or "all",
        "owner": sid or "web",
    }


def try_handle_pending_delete_cancel(
    session: Any,
    sid: str | None,
    user_text: str,
) -> bool:
    """UX_CORRECTION_DELETE_CANCEL: 削除確認待ち + キャンセル発話なら legacy pending を復元する。"""
    try:
        from config.llm_flags import is_ux_correction_delete_cancel_enabled
    except ImportError:
        return False
    if not is_ux_correction_delete_cancel_enabled():
        return False
    if not is_pending_delete_cancel(user_text):
        return False
    if not is_awaiting_memory_delete_confirmation(
        session,
        allow_bot_confirm_fallback=True,
    ):
        return False
    _ensure_legacy_pending_for_delete(session, sid)
    return True


def try_answer_pending_delete_cancel(
    session: Any,
    sid: str | None,
    user_text: str,
) -> Optional[ResponseTuple]:
    """counseling 直前の最終ガード: 削除キャンセルを SessionOps で返す。"""
    if not try_handle_pending_delete_cancel(session, sid, user_text):
        return None
    resp = _handle_web_delete(session, sid, user_text)
    _sync_dialogue_state(session, sid)
    return resp


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


def _handle_web_recorded_items(
    session: Any,
    sid: str | None,
    user_text: str,
) -> ResponseTuple:
    from src.agents.session_agent import _build_bot, _ok_response, _persist_session_messages
    from src.services.status_diagnosis_builder import build_session_recorded_items_status
    from src.utils.agent_trace import log_agent_step

    snapshot = dict(session) if isinstance(session, dict) else {}
    profile = snapshot.get("user_attributes") or {}
    sage_diag = build_session_recorded_items_status(
        session_snapshot=snapshot,
        profile=profile,
    ).to_client_dict()
    message = str(sage_diag.get("message") or "")
    bot = _build_bot(
        session, sid, sage_diag=sage_diag, legacy_message=message, kind="recorded_items"
    )
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionOps", "web_session_recorded_items", sid=sid)
    return _ok_response(session)


def _handle_web_history_overview(
    session: Any,
    sid: str | None,
    user_text: str,
) -> ResponseTuple:
    from src.agents.session_agent import _build_bot, _ok_response, _persist_session_messages
    from src.services.status_diagnosis_builder import build_session_history_overview
    from src.utils.agent_trace import log_agent_step

    snapshot = dict(session) if isinstance(session, dict) else {}
    sage_diag = build_session_history_overview(session_snapshot=snapshot).to_client_dict()
    message = str(sage_diag.get("message") or "")
    bot = _build_bot(
        session, sid, sage_diag=sage_diag, legacy_message=message, kind="history_overview"
    )
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionOps", "web_session_history_overview", sid=sid)
    return _ok_response(session)


def _clear_web_session_data(session: Any, sid: str | None) -> None:
    if session is not None and hasattr(session, "__setitem__"):
        session["messages"] = []
        session.pop("user_attributes", None)
        session.pop("last_triage_result", None)
        session.pop("counseling_mode", None)
        session.pop("concierge_state", None)
        session.pop("triage_clarify_sent", None)
    try:
        from src.dialogue.context import load_dialogue_context, save_dialogue_context

        ctx = load_dialogue_context(session)
        for key in ("counseling", "concierge", "routing", "handoff"):
            ctx.pop(key, None)
        ctx["flags"] = {}
        save_dialogue_context(session, ctx, dual_write=True)
    except Exception:
        logger.debug("web session clear dialogue_state skipped", exc_info=True)
    if sid:
        try:
            from src.services.session_manager import get_session_from_db, save_session_to_db

            data = get_session_from_db(sid) or {"session_id": sid, "messages": []}
            data["messages"] = []
            data.pop("user_attributes", None)
            data.pop("pending_memory_delete", None)
            save_session_to_db(sid, data)
        except Exception:
            logger.debug("web session clear db skipped", exc_info=True)


def _handle_web_delete(
    session: Any,
    sid: str | None,
    user_text: str,
) -> ResponseTuple:
    from src.agents.session_agent import (
        _build_bot,
        _clear_pending_memory_delete,
        _is_delete_confirm_no,
        _is_delete_confirm_yes,
        _ok_response,
        _persist_session_messages,
    )
    from src.services.status_diagnosis_builder import build_notice_status
    from src.utils.agent_trace import log_agent_step

    if _is_delete_confirm_no(user_text):
        _clear_pending_memory_delete(session, sid)
        msg = "削除はキャンセルしました。記憶はそのまま残しています。"
        sage_diag = build_notice_status(
            msg,
            title="記憶の削除",
            kind="memory_delete_cancelled",
        ).to_client_dict()
        bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete_cancelled")
        _persist_session_messages(session, sid, user_text, bot)
        log_agent_step(None, "SessionOps", "web_memory_delete_cancelled", sid=sid)
        return _ok_response(session)

    if session.get("pending_memory_delete"):
        from src.agents.session_agent import _is_pending_delete_explain_request

        if _is_pending_delete_explain_request(user_text):
            msg = (
                "現在、記憶の削除確認をお待ちしています。"
                "削除対象は、この端末の相談履歴と保存情報です。"
                "実行する場合は「削除する」、やめる場合は「キャンセル」とお送りください。"
            )
            sage_diag = build_notice_status(
                msg,
                title="記憶の削除（確認中）",
                kind="memory_delete_explain",
            ).to_client_dict()
            bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete_explain")
            _persist_session_messages(session, sid, user_text, bot)
            log_agent_step(None, "SessionOps", "web_memory_delete_explain", sid=sid)
            return _ok_response(session)

    if session.get("pending_memory_delete") and not _is_delete_confirm_yes(user_text):
        msg = (
            "削除する場合は「削除する」、やめる場合は「キャンセル」とお送りください。"
            "（「はい」「いいえ」でも受け付けます）"
        )
        sage_diag = build_notice_status(
            msg,
            title="記憶の削除（確認）",
            kind="memory_delete_pending",
        ).to_client_dict()
        bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete_pending")
        _persist_session_messages(session, sid, user_text, bot)
        return _ok_response(session)

    if session.get("pending_memory_delete") and _is_delete_confirm_yes(user_text):
        _clear_web_session_data(session, sid)
        session.pop("pending_memory_delete", None)
        msg = "この端末の相談履歴と保存情報を削除しました。"
        sage_diag = build_notice_status(
            msg,
            title="記憶の削除",
            kind="memory_delete",
        ).to_client_dict()
        bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete")
        _persist_session_messages(session, sid, user_text, bot)
        log_agent_step(None, "SessionOps", "web_memory_deleted", sid=sid)
        return _ok_response(session)

    session["pending_memory_delete"] = {"scope": "all", "owner": sid or "web"}
    msg = (
        "このチャットの相談履歴と保存情報を削除します。"
        "よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。"
    )
    sage_diag = build_notice_status(
        msg,
        title="記憶の削除（確認）",
        kind="memory_delete_confirm",
    ).to_client_dict()
    bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete_confirm")
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionOps", "web_memory_delete_confirm_requested", sid=sid)
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
    Web: delete / summarize / status
    """
    _sync_dialogue_state(session, sid)

    from src.services.line_user_memory import is_line_memory_session

    triage = triage_result or {}
    router_dispatch = bool(triage.get("_intent_router_dispatch"))
    forced_session_intent = str(triage.get("session_intent") or "").strip()

    if router_dispatch and forced_session_intent == "pending_clear":
        resp = try_answer_pending_delete_cancel(session, sid, user_text)
        if resp is not None:
            return resp

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

    if try_handle_pending_delete_cancel(session, sid, user_text):
        resp = _handle_web_delete(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp

    intent = classify_session_intent(user_text, triage_result=triage_result)
    if router_dispatch and intent == "none" and forced_session_intent in (
        "delete",
        "summarize",
        "status",
    ):
        intent = forced_session_intent  # type: ignore[assignment]
    detail = None
    try:
        from config.llm_flags import is_ux_session_ops_real_data_enabled

        if is_ux_session_ops_real_data_enabled():
            detail = classify_session_ops_detail(user_text, triage_result=triage_result)
    except ImportError:
        detail = None

    if intent == "delete" or session.get("pending_memory_delete"):
        resp = _handle_web_delete(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    if detail == "recorded_items":
        resp = _handle_web_recorded_items(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    if detail == "history_overview":
        resp = _handle_web_history_overview(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    if intent == "status" or detail == "status":
        resp = _handle_web_status(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    if intent == "summarize" or detail == "summarize":
        resp = _handle_web_summarize(session, sid, user_text, client)
        _sync_dialogue_state(session, sid)
        return resp
    if router_dispatch and forced_session_intent == "session_admin":
        if is_pending_delete_cancel(user_text):
            resp = try_answer_pending_delete_cancel(session, sid, user_text)
            if resp is not None:
                return resp
        detail = classify_session_ops_detail(user_text, triage_result=triage_result)
        if detail == "recorded_items":
            resp = _handle_web_recorded_items(session, sid, user_text)
            _sync_dialogue_state(session, sid)
            return resp
        if detail == "history_overview":
            resp = _handle_web_history_overview(session, sid, user_text)
            _sync_dialogue_state(session, sid)
            return resp
        if detail in ("status", "summarize", "delete"):
            if detail == "delete":
                resp = _handle_web_delete(session, sid, user_text)
            elif detail == "summarize":
                resp = _handle_web_summarize(session, sid, user_text, client)
            else:
                resp = _handle_web_status(session, sid, user_text)
            _sync_dialogue_state(session, sid)
            return resp
        resp = _handle_web_status(session, sid, user_text)
        _sync_dialogue_state(session, sid)
        return resp
    return None
