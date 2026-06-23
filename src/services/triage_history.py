"""
トリアージ用会話履歴の整形
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.routing_config import triage_history_messages


def get_recent_messages(
    session: Any,
    sid: Optional[str],
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    from src.services.line_user_memory import is_line_memory_session

    if is_line_memory_session(sid, session):
        from src.services.line_memory_context import get_memory_aware_recent_messages

        return get_memory_aware_recent_messages(session, sid, limit=limit)

    n = limit if limit is not None else triage_history_messages()
    if n <= 0:
        return []
    messages: List[Dict[str, Any]] = []
    if session and session.get("messages"):
        messages = list(session.get("messages") or [])
    elif sid:
        try:
            from src.services.session_manager import get_session_from_db

            data = get_session_from_db(sid) or {}
            messages = list(data.get("messages") or [])
        except Exception:
            messages = []
    return messages[-n:] if len(messages) > n else messages


def format_triage_history_block(messages: List[Dict[str, Any]]) -> str:
    if not messages:
        return "（なし）"
    from src.services.line_memory_context import compress_message_for_llm

    lines = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        compressed = compress_message_for_llm(msg)
        role = compressed.get("type") or "user"
        content = (compressed.get("content") or "").strip()[:300]
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "（なし）"


def history_digest(messages: List[Dict[str, Any]]) -> str:
    import hashlib

    block = format_triage_history_block(messages)
    if block == "（なし）":
        return ""
    return hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]


def memory_digest(memory_block: str | None) -> str:
    """長期記憶ブロック（プロファイル + 要約）のキャッシュキー用ダイジェスト。"""
    import hashlib

    text = (memory_block or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
