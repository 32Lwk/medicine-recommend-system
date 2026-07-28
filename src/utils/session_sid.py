"""HTTP リクエストの sid と in-memory session の整合性を保つ。"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def bind_request_session_sid(session: Any, sid: Optional[str]) -> None:
    """リクエスト sid を session['_id'] に束縛する（不一致時は request sid を正とする）。"""
    if not sid or session is None:
        return
    bound = session.get("_id") if hasattr(session, "get") else None
    if bound and str(bound) != str(sid):
        logger.warning("session sid rebinding: bound=%s request=%s", bound, sid)
    if hasattr(session, "__setitem__"):
        session["_id"] = sid


def session_sid_matches(session: Any, sid: Optional[str]) -> bool:
    if not sid or session is None:
        return True
    bound = session.get("_id") if hasattr(session, "get") else None
    if not bound:
        return True
    return str(bound) == str(sid)


def warn_session_sid_mismatch(
    session: Any,
    sid: Optional[str],
    *,
    context: str,
) -> bool:
    """不一致なら error ログを出し False。"""
    if session_sid_matches(session, sid):
        return True
    bound = session.get("_id") if hasattr(session, "get") else None
    logger.error(
        "session sid mismatch context=%s bound=%s request=%s",
        context,
        bound,
        sid,
    )
    return False


def resolve_effective_session_id(
    session: Any,
    session_id: Optional[str],
) -> Optional[str]:
    """ログ・永続化用 sid。request sid を session['_id'] より優先。"""
    if session_id:
        if session is not None and hasattr(session, "get"):
            bound = session.get("_id")
            if bound and str(bound) != str(session_id):
                logger.warning(
                    "resolve_effective_session_id: bound=%s overrides with request=%s",
                    bound,
                    session_id,
                )
        return str(session_id)
    if session is not None and hasattr(session, "get"):
        for key in ("_id", "session_id"):
            val = session.get(key)
            if val:
                return str(val)
    return None
