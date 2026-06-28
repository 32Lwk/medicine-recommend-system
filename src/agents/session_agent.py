"""SessionAgent — セッション操作（削除・要約・ステータス）の統合ハンドラ。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Optional, Tuple

from src.agents.memory_delete_agent import (
    _looks_like_delete_request,
    classify_memory_delete_intent,
    execute_memory_delete,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]
SessionIntent = Literal["delete", "summarize", "status", "none"]

_DELETE_CONFIRM_YES = frozenset(
    {"はい", "削除する", "削除して", "消して", "yes", "ok", "了解", "お願いします"}
)
_DELETE_CONFIRM_NO = frozenset(
    {"いいえ", "キャンセル", "やめる", "しない", "no", "やめて"}
)

_STATUS_HINTS = (
    r"ステータス",
    r"状態を教えて",
    r"状況を教えて",
    r"現在の状態",
    r"今の状態",
    r"セッション.*状態",
    r"記憶.*状態",
    r"何が記録",
    r"記録.*教えて",
)

_SUMMARIZE_HINTS = (
    r"履歴を要約",
    r"履歴要約",
    r"履歴を教えて",
    r"相談履歴",
    r"これまでの相談",
    r"会話を要約",
    r"チャット.*要約",
    r"要約して",
    r"まとめて",
)

_SESSION_ADMIN_LOOSE_DELETE = (
    r"履歴.*消",
    r"記憶.*消",
    r"データ.*消",
    r"全部消",
    r"すべて消",
    r"全て消",
    r"忘れて",
)

_SESSION_ADMIN_LOOSE_SUMMARIZE = (
    r"要約",
    r"まとめ",
)

_SESSION_ADMIN_LOOSE_STATUS = (
    r"ステータス",
    r"状態",
    r"状況",
)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False


def classify_session_intent(
    user_text: str,
    *,
    triage_result: dict[str, Any] | None = None,
) -> SessionIntent:
    """削除・要約・ステータス意図を分類する。"""
    t = (user_text or "").strip()
    if not t:
        return "none"

    if _looks_like_delete_request(t):
        return "delete"
    if _matches_any(t, _SUMMARIZE_HINTS):
        return "summarize"
    if _matches_any(t, _STATUS_HINTS):
        return "status"

    sub = str((triage_result or {}).get("subcategory") or "").lower()
    meta_intent = str((triage_result or {}).get("concierge_intent") or "").lower()
    session_intent = str((triage_result or {}).get("session_intent") or "").lower()
    triage_session = (
        "session_admin" in sub
        or meta_intent == "session_ops"
        or session_intent in ("delete", "summarize", "status")
    )
    if not triage_session:
        return "none"

    if session_intent in ("delete", "summarize", "status"):
        return session_intent  # type: ignore[return-value]

    if _matches_any(t, _SESSION_ADMIN_LOOSE_DELETE):
        return "delete"
    if _matches_any(t, _SESSION_ADMIN_LOOSE_SUMMARIZE):
        return "summarize"
    if _matches_any(t, _SESSION_ADMIN_LOOSE_STATUS):
        return "status"
    return "none"


def probe_session_admin_intent(user_text: str) -> SessionIntent | None:
    """トリアージ前の高信頼キーワードプローブ。"""
    intent = classify_session_intent(user_text)
    return intent if intent != "none" else None


def _normalize_confirm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def _is_delete_confirm_yes(text: str) -> bool:
    norm = _normalize_confirm(text)
    return norm in _DELETE_CONFIRM_YES or norm.endswith("削除する")


def _is_delete_confirm_no(text: str) -> bool:
    norm = _normalize_confirm(text)
    if norm in _DELETE_CONFIRM_NO:
        return True
    cancel_patterns = (
        r"消さない",
        r"消すのはやめ",
        r"削除しない",
        r"削除.*やめ",
        r"やっぱり.*やめ",
    )
    return any(re.search(pat, norm) for pat in cancel_patterns)


def is_pending_delete_cancel(text: str) -> bool:
    """pending_memory_delete 確認中のキャンセル発話。"""
    return _is_delete_confirm_no(text)


def _persist_session_messages(
    session: Any,
    sid: str | None,
    user_text: str,
    bot: dict[str, Any],
    *,
    profile: dict[str, Any] | None = None,
) -> None:
    from src.services.line_user_memory import profile_to_user_attributes

    session.setdefault("messages", []).append({"type": "user", "content": user_text})
    session["messages"].append(bot)
    if profile is not None and hasattr(session, "__setitem__"):
        session["user_attributes"] = profile_to_user_attributes(profile)
    try:
        from src.services.session_manager import get_session_from_db, save_session_to_db

        if sid:
            data = get_session_from_db(sid) or {"session_id": sid, "messages": []}
            data["messages"] = list(session.get("messages") or [])
            if profile is not None:
                data["user_attributes"] = profile_to_user_attributes(profile)
            if session.get("pending_memory_delete"):
                data["pending_memory_delete"] = session.get("pending_memory_delete")
            elif "pending_memory_delete" in data:
                data.pop("pending_memory_delete", None)
            save_session_to_db(sid, data)
    except Exception:
        logger.warning("SessionAgent session persist failed sid=%s", sid, exc_info=True)


def _ok_response(session: Any) -> ResponseTuple:
    return ({"status": "ok", "message_count": len(session.get("messages") or [])}, 200)


def _build_bot(
    session: Any,
    sid: str | None,
    *,
    sage_diag: dict[str, Any],
    legacy_message: str,
    kind: str,
) -> dict[str, Any]:
    from src.services.sage_bot_response import build_bot_response

    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_message,
        session_agent=True,
        session_agent_kind=kind,
    )


def _clear_pending_memory_delete(session: Any, sid: str | None) -> None:
    session.pop("pending_memory_delete", None)
    try:
        from config.llm_flags import is_chat_pipeline_v2_for_session

        if is_chat_pipeline_v2_for_session(sid):
            from src.dialogue.context import load_dialogue_context, save_dialogue_context

            ctx = load_dialogue_context(session)
            pending = ctx.get("pending") or {}
            pending.pop("session_delete", None)
            ctx["pending"] = pending
            save_dialogue_context(session, ctx)
    except Exception:
        logger.debug("dialogue_state pending clear skipped sid=%s", sid, exc_info=True)
    try:
        from src.services.session_manager import get_session_from_db, save_session_to_db

        if sid:
            data = get_session_from_db(sid) or {"session_id": sid}
            data.pop("pending_memory_delete", None)
            save_session_to_db(sid, data)
    except Exception:
        logger.warning("SessionAgent clear pending failed sid=%s", sid, exc_info=True)


def _pending_cancelled_by_medical_priority(
    user_text: str,
    *,
    triage_result: dict[str, Any] | None = None,
) -> bool:
    """削除確認待ち中に Physical/Emergency 症状が来たら pending を解消する。"""
    triage = triage_result or {}
    category = str(triage.get("category") or "")
    if category in ("Physical", "Emergency"):
        from config.routing_config import triage_confidence_threshold

        if float(triage.get("confidence") or 0.0) >= triage_confidence_threshold():
            return True
    from src.utils.input_helpers import has_explicit_symptom_signal, has_fever_signal

    text = (user_text or "").strip()
    if has_fever_signal(text) or has_explicit_symptom_signal(text):
        return True
    return False


def _delete_plan_for_intent(
    user_text: str,
    client: Any,
    *,
    triage_result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """削除意図に対する plan。triage Physical 等では delete を強制しない。"""
    plan = classify_memory_delete_intent(user_text, client)
    if plan.get("is_delete_request"):
        return plan

    session_intent = str((triage_result or {}).get("session_intent") or "").lower()
    if session_intent == "delete":
        return {"is_delete_request": True, "scope": "all"}

    if _looks_like_delete_request(user_text) or _matches_any(user_text, _SESSION_ADMIN_LOOSE_DELETE):
        return {"is_delete_request": True, "scope": "all"}

    return None


def _handle_delete_confirm(
    session: Any,
    sid: str | None,
    user_text: str,
    owner: str,
) -> ResponseTuple:
    from src.services.line_user_memory import load_line_memory, profile_to_user_attributes
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
        log_agent_step(None, "SessionAgent", "memory_delete_cancelled", sid=owner)
        return _ok_response(session)

    if not _is_delete_confirm_yes(user_text):
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

    plan = {
        "is_delete_request": True,
        "scope": "all",
        "profile_keys": [],
        "clear_summaries": True,
        "confirmation_message": "保存していた相談記憶とプロファイル情報を削除しました。",
    }
    execute_memory_delete(owner, plan)
    session.pop("pending_memory_delete", None)
    refreshed, _ = load_line_memory(owner)
    if session is not None and hasattr(session, "__setitem__"):
        session["user_attributes"] = profile_to_user_attributes(refreshed)

    msg = plan["confirmation_message"]
    sage_diag = build_notice_status(
        msg,
        title="記憶の削除",
        kind="memory_delete",
    ).to_client_dict()
    bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete")
    _persist_session_messages(session, sid, user_text, bot, profile=refreshed)
    log_agent_step(
        None,
        "SessionAgent",
        "memory_deleted",
        sid=owner,
        payload={"scope": "all", "confirmed": True},
    )
    return _ok_response(session)


def _request_delete_confirmation(
    session: Any,
    sid: str | None,
    user_text: str,
    owner: str,
) -> ResponseTuple:
    from src.services.status_diagnosis_builder import build_notice_status
    from src.utils.agent_trace import log_agent_step

    session["pending_memory_delete"] = {"scope": "all", "owner": owner}
    msg = (
        "保存している相談記憶・プロファイル・要約をすべて削除します。"
        "よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。"
    )
    sage_diag = build_notice_status(
        msg,
        title="記憶の削除（確認）",
        kind="memory_delete_confirm",
        hints=["削除後は元に戻せません"],
    ).to_client_dict()
    bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=msg, kind="delete_confirm")
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionAgent", "memory_delete_confirm_requested", sid=owner)
    return _ok_response(session)


def _summarize_from_long_term(summaries: list[dict[str, Any]]) -> str | None:
    parts: list[str] = []
    for item in summaries[-5:]:
        text = str((item or {}).get("summary_text") or "").strip()
        if text:
            parts.append(text)
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return "\n\n".join(f"・{p}" for p in parts)


def _summarize_session_llm(session: Any, client: Any) -> str | None:
    from src.agents.episode_summary_agent import _compress_messages_for_summary

    messages = session.get("messages") or []
    transcript = _compress_messages_for_summary(messages)
    if not transcript.strip():
        return None

    try:
        from src.core.llm_client import chat_completion_create

        prompt = f"""以下の相談セッションを200字以内で要約してください（日本語・箇条書き可）。

【会話】
{transcript}
"""
        response = chat_completion_create(
            client,
            model_role="triage",
            path="session_agent.summarize",
            messages=[
                {"role": "system", "content": "医薬品相談の要約のみ。簡潔に。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        logger.warning("SessionAgent summarize LLM failed", exc_info=True)
        return None


def _handle_summarize(
    session: Any,
    sid: str | None,
    user_text: str,
    owner: str,
    client: Any,
) -> ResponseTuple:
    from src.services.line_user_memory import load_line_memory
    from src.services.status_diagnosis_builder import build_notice_status
    from src.utils.agent_trace import log_agent_step

    _, summaries = load_line_memory(owner)
    summary_text = _summarize_from_long_term(summaries)
    source = "long_term_memory"
    if not summary_text:
        summary_text = _summarize_session_llm(session, client)
        source = "session_llm"
    if not summary_text:
        summary_text = "要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。"

    sage_diag = build_notice_status(
        summary_text,
        title="相談履歴の要約",
        kind="session_summary",
        show_feedback=True,
    ).to_client_dict()
    bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=summary_text, kind="summarize")
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(
        None,
        "SessionAgent",
        "session_summarized",
        sid=owner,
        payload={"source": source},
    )
    return _ok_response(session)


def _handle_status(
    session: Any,
    sid: str | None,
    user_text: str,
    owner: str,
) -> ResponseTuple:
    from src.services.line_user_memory import load_line_memory
    from src.services.session_manager import get_line_session_admin_snapshot
    from src.services.status_diagnosis_builder import build_session_integrated_status
    from src.utils.agent_trace import log_agent_step

    profile, summaries = load_line_memory(owner)
    snapshot = get_line_session_admin_snapshot(owner) if owner else None
    sage_diag = build_session_integrated_status(
        session_snapshot=snapshot or dict(session) if isinstance(session, dict) else {},
        profile=profile,
        summaries=summaries,
    ).to_client_dict()
    message = str(sage_diag.get("message") or "")
    bot = _build_bot(session, sid, sage_diag=sage_diag, legacy_message=message, kind="status")
    _persist_session_messages(session, sid, user_text, bot)
    log_agent_step(None, "SessionAgent", "session_status", sid=owner)
    return _ok_response(session)


def try_handle_session_request(
    session: Any,
    sid: str | None,
    user_text: str,
    client: Any,
    *,
    triage_result: dict[str, Any] | None = None,
) -> Optional[ResponseTuple]:
    """セッション操作依頼なら同期処理して応答を返す。"""
    from src.services.line_user_memory import is_line_memory_session, resolve_memory_owner_sid

    if not is_line_memory_session(sid, session):
        return None

    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        return None

    if session.get("pending_memory_delete"):
        if _pending_cancelled_by_medical_priority(
            user_text,
            triage_result=triage_result,
        ):
            _clear_pending_memory_delete(session, sid)
            try:
                from src.dialogue.sync_legacy import mirror_pending_medical_cancel

                mirror_pending_medical_cancel(session, sid)
            except Exception:
                logger.debug(
                    "SessionAgent: mirror_pending_medical_cancel skipped sid=%s",
                    sid,
                    exc_info=True,
                )
            logger.info(
                "SessionAgent: pending delete cancelled for medical priority sid=%s",
                sid,
            )
            return None
        return _handle_delete_confirm(session, sid, user_text, owner)

    intent = classify_session_intent(user_text, triage_result=triage_result)
    if intent == "none":
        return None

    if intent == "delete":
        triage_cat = str((triage_result or {}).get("category") or "")
        if triage_cat in ("Physical", "Emergency"):
            return None
        plan = _delete_plan_for_intent(user_text, client, triage_result=triage_result)
        if not plan:
            return None
        return _request_delete_confirmation(session, sid, user_text, owner)

    if intent == "summarize":
        return _handle_summarize(session, sid, user_text, owner, client)

    if intent == "status":
        return _handle_status(session, sid, user_text, owner)

    return None


def execute_confirmed_memory_delete(
    line_sid: str,
    session: Any,
) -> tuple[str, dict[str, Any]]:
    """Quick Reply / postback からの削除確定（LINE 専用補助）。"""
    from src.services.line_user_memory import load_line_memory, profile_to_user_attributes
    from src.services.status_diagnosis_builder import build_notice_status
    from src.utils.agent_trace import log_agent_step

    plan = {
        "is_delete_request": True,
        "scope": "all",
        "profile_keys": [],
        "clear_summaries": True,
        "confirmation_message": "保存していた相談記憶とプロファイル情報を削除しました。",
    }
    execute_memory_delete(line_sid, plan)
    session.pop("pending_memory_delete", None)
    refreshed, _ = load_line_memory(line_sid)
    if hasattr(session, "__setitem__"):
        session["user_attributes"] = profile_to_user_attributes(refreshed)
    msg = plan["confirmation_message"]
    sage_diag = build_notice_status(
        msg,
        title="記憶の削除",
        kind="memory_delete",
    ).to_client_dict()
    log_agent_step(
        None,
        "SessionAgent",
        "memory_deleted",
        sid=line_sid,
        payload={"scope": "all", "confirmed": True, "via": "postback"},
    )
    return msg, sage_diag
