"""会話履歴解決 — v2 時 ContextProvider、OFF 時 legacy（Wave 2）。"""
from __future__ import annotations

from typing import Any

from config.llm_flags import is_chat_pipeline_v2_for_session


def resolve_conversation_history(
    session: Any,
    sid: str | None,
    *,
    agent_kind: str = "default",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    agent_kind 別履歴窓。v2 ON: ContextProvider、OFF: get_recent_messages。
    """
    if is_chat_pipeline_v2_for_session(sid):
        from src.dialogue.context_provider import build_context_bundle

        bundle = build_context_bundle(session, sid, agent_kind=agent_kind)
        msgs = list(bundle.messages)
        if limit is not None and len(msgs) > limit:
            msgs = msgs[-limit:]
        return msgs

    from src.services.triage_history import get_recent_messages

    if limit is not None:
        return get_recent_messages(session, sid, limit=limit)
    return get_recent_messages(session, sid)


def resolve_counseling_history(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    カウンセリング / Emotional 経路向け履歴。
    v2 ON: counseling 窓 + 長期記憶 system 行、OFF: get_counseling_conversation_history。
    """
    if is_chat_pipeline_v2_for_session(sid):
        from src.dialogue.context_provider import build_context_bundle

        bundle = build_context_bundle(session, sid, agent_kind="counseling")
        out: list[dict[str, Any]] = []
        if bundle.memory_block:
            out.append({"type": "system", "content": bundle.memory_block})
        out.extend(bundle.messages)
        if limit is not None and len(out) > limit:
            out = out[-limit:]
        return out

    from src.services.line_memory_context import get_counseling_conversation_history

    history = get_counseling_conversation_history(session, sid)
    if limit is not None and len(history) > limit:
        history = history[-limit:]
    return history


def resolve_emergency_history(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """緊急チェック向けの最小遅延履歴窓。"""
    return resolve_conversation_history(session, sid, agent_kind="emergency", limit=limit)


def resolve_emergency_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """緊急チェック向け — resolve 失敗時 legacy フォールバック。"""
    try:
        return resolve_emergency_history(session, sid, limit=limit)
    except Exception:
        return resolve_conversation_history_with_fallback(
            session, sid, agent_kind="emergency", limit=limit
        )


def resolve_physical_history(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Physical / 推奨フロー向けの拡張履歴窓。"""
    return resolve_conversation_history(session, sid, agent_kind="physical", limit=limit)


def resolve_physical_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Physical 向け — resolve 失敗時 legacy にフォールバック。"""
    try:
        return resolve_physical_history(session, sid, limit=limit)
    except Exception:
        return resolve_conversation_history_with_fallback(
            session, sid, agent_kind="physical", limit=limit
        )


def resolve_emotional_history(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Emotional / カウンセリング系の emotional 窓。"""
    return resolve_conversation_history(session, sid, agent_kind="emotional", limit=limit)


def resolve_emotional_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Emotional 向け — resolve 失敗時 legacy にフォールバック。"""
    try:
        return resolve_emotional_history(session, sid, limit=limit)
    except Exception:
        return resolve_counseling_history_with_fallback(session, sid, limit=limit)


def resolve_concierge_history(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Concierge intent / payload 用の直近履歴。"""
    if is_chat_pipeline_v2_for_session(sid):
        return resolve_conversation_history(
            session, sid, agent_kind="concierge", limit=limit
        )
    msgs = session.get("messages") if session is not None and hasattr(session, "get") else []
    out = list(msgs or [])
    tail = limit if limit is not None else 10
    if len(out) > tail:
        out = out[-tail:]
    return out


def resolve_concierge_log_history(
    session: Any,
    sid: str | None,
) -> list[dict[str, Any]]:
    """Concierge 詳細ログ用（カウンセリング経路と同形式）。"""
    return resolve_counseling_history_with_fallback(session, sid)


def resolve_counseling_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Wave 2 ルート向け — resolve 失敗時 legacy にフォールバック。"""
    try:
        return resolve_counseling_history(session, sid, limit=limit)
    except Exception:
        from src.services.line_memory_context import get_counseling_conversation_history

        history = get_counseling_conversation_history(session, sid)
        if limit is not None and len(history) > limit:
            history = history[-limit:]
        return history


def resolve_concierge_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Concierge 向け — resolve 失敗時 legacy にフォールバック。"""
    try:
        return resolve_concierge_history(session, sid, limit=limit)
    except Exception:
        msgs = session.get("messages") if session is not None and hasattr(session, "get") else []
        out = list(msgs or [])
        tail = limit if limit is not None else 10
        if len(out) > tail:
            out = out[-tail:]
        return out


def resolve_conversation_history_with_fallback(
    session: Any,
    sid: str | None,
    *,
    agent_kind: str = "default",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Triage / enrich 向け — resolve 失敗時 get_recent_messages。"""
    try:
        return resolve_conversation_history(
            session, sid, agent_kind=agent_kind, limit=limit
        )
    except Exception:
        from src.services.triage_history import get_recent_messages

        if limit is not None:
            return get_recent_messages(session, sid, limit=limit)
        return get_recent_messages(session, sid)
