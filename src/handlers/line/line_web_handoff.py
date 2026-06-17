"""LINE → Web ワンタイム引き継ぎトークン。"""
from __future__ import annotations

import logging
import secrets
import time
from typing import Any

logger = logging.getLogger(__name__)

_HANDOFF_TTL_SEC = 30 * 60
_tokens: dict[str, dict[str, Any]] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _tokens.items() if v.get("expires_at", 0) <= now]
    for k in expired:
        _tokens.pop(k, None)


def issue_handoff_token(line_sid: str) -> str | None:
    """LINE セッション ID からワンタイムトークンを発行する。"""
    from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    from src.services.session_manager import get_session_from_db

    line_sid = normalize_line_session_id(line_sid) or line_sid
    if not is_line_session_id(line_sid):
        return None

    session = get_session_from_db(line_sid)
    if not session:
        return None

    _purge_expired()
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "line_sid": line_sid,
        "expires_at": time.time() + _HANDOFF_TTL_SEC,
        "used": False,
    }
    logger.info("LINE web handoff token issued line_sid=%s", line_sid)
    return token


def redeem_handoff_token(token: str) -> dict[str, Any] | None:
    """
    トークンを検証し LINE セッションスナップショットを返す。
    1 回限り。失効・二重使用時は None。
    """
    if not token:
        return None
    _purge_expired()
    entry = _tokens.get(token)
    if not entry:
        return None
    if entry.get("used"):
        return None
    if entry.get("expires_at", 0) <= time.time():
        _tokens.pop(token, None)
        return None

    from src.services.session_manager import get_session_from_db

    line_sid = entry.get("line_sid")
    session = get_session_from_db(line_sid) if line_sid else None
    if not session:
        _tokens.pop(token, None)
        return None

    entry["used"] = True
    return {
        "line_sid": line_sid,
        "messages": (session.get("messages") or []).copy(),
        "user_attributes": dict(session.get("user_attributes") or {}),
        "username": session.get("username"),
        "detected_language": session.get("detected_language") or session.get("language"),
    }


def create_web_session_from_handoff(
    snapshot: dict[str, Any],
    *,
    request: Any,
) -> str:
    """引き継ぎスナップショットから新 Web セッションを作成し sid を返す。"""
    import random
    import time as _time

    from src.services.session_manager import ensure_session_persisted, get_next_user_number

    sid = str(int(_time.time() * 1000000)) + str(random.randint(100000, 999999))
    username = snapshot.get("username") or f"ユーザー{get_next_user_number()}"
    attrs = snapshot.get("user_attributes") or {}
    payload = {
        "messages": snapshot.get("messages") or [],
        "username": username,
        "user_attributes": attrs,
        "session_active": True,
        "handoff_from_line": snapshot.get("line_sid"),
    }
    if snapshot.get("detected_language"):
        payload["detected_language"] = snapshot["detected_language"]
    ensure_session_persisted(sid, payload, request)
    return sid
