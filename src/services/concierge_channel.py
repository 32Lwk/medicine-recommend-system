"""Concierge チャネル別 UX（Web / LINE / admin）。"""
from __future__ import annotations

from typing import Optional

_LINE_ARCHITECTURE_FOLLOW_UP_HINT = (
    "詳しく知りたい場合は「詳しく」と送ってください。"
)


def is_concierge_line_channel(session_id: Optional[str]) -> bool:
    if not session_id:
        return False
    try:
        from src.handlers.line.line_session import is_line_session_id

        return is_line_session_id(session_id)
    except ImportError:
        return str(session_id).startswith("line:")


def resolve_concierge_channel(session_id: Optional[str]) -> str:
    """web | line（admin は web と同 deep 扱い）。"""
    return "line" if is_concierge_line_channel(session_id) else "web"


def line_architecture_follow_up_hint(*, deep: bool) -> Optional[str]:
    if deep:
        return None
    return _LINE_ARCHITECTURE_FOLLOW_UP_HINT
