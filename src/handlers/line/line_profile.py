"""LINE Messaging API からユーザープロフィールを取得してセッションへ保存。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from config.line_config import get_line_channel_access_token
from src.core.language_utils import sync_language_from_line_profile
from src.handlers.line.line_reply import get_json
from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id, user_id_from_line_sid
from src.services.session_lifecycle import append_lifecycle_event
from src.services.session_manager import (
    get_session_from_db,
    get_session_from_memory,
    save_session_to_db,
    touch_session_in_memory,
)

logger = logging.getLogger(__name__)

LINE_PROFILE_URL = "https://api.line.me/v2/bot/profile/{userId}"

# Messaging API Get profile で取得できる全フィールド
LINE_PROFILE_FIELDS = ("userId", "displayName", "pictureUrl", "statusMessage", "language")


async def fetch_line_user_profile(user_id: str) -> Optional[dict[str, Any]]:
    """GET /v2/bot/profile/{userId}"""
    token = get_line_channel_access_token()
    if not user_id or not token:
        return None
    url = LINE_PROFILE_URL.format(userId=user_id)
    data = await get_json(url, log_label="profile")
    if not data:
        return None
    profile = {k: data.get(k) for k in LINE_PROFILE_FIELDS if data.get(k) is not None}
    profile["fetched_at"] = datetime.now().isoformat()
    return profile


def apply_line_profile_to_session(
    session: Any,
    profile: dict[str, Any],
    *,
    sid: Optional[str] = None,
) -> None:
    """session と DB の line_profile / username を更新。"""
    if not profile:
        return
    old_display = ""
    if hasattr(session, "get"):
        old_prof = session.get("line_profile")
        if isinstance(old_prof, dict):
            old_display = (old_prof.get("displayName") or "").strip()

    session["line_profile"] = profile
    display = (profile.get("displayName") or "").strip()
    if display:
        session["username"] = display
    if hasattr(session, "pop"):
        session.pop("line_profile_error", None)
    sync_language_from_line_profile(session)

    if not sid:
        return
    if is_line_session_id(sid):
        session_data = get_session_from_memory(sid) or {"session_id": sid, "messages": []}
    else:
        session_data = get_session_from_db(sid) or {"session_id": sid, "messages": []}
    session_data["line_profile"] = profile
    if display:
        session_data["username"] = display
    session_data.pop("line_profile_error", None)
    sync_language_from_line_profile(session, session_data)
    if display and display != old_display:
        append_lifecycle_event(
            session_data,
            "profile_fetched",
            source="line_profile.apply_line_profile_to_session",
            detail=display or profile.get("userId"),
        )
    save_session_to_db(sid, session_data)
    touch_session_in_memory(sid, session_data)


async def ensure_line_user_profile(
    user_id: str,
    session: Any,
    *,
    sid: Optional[str] = None,
    force_refresh: bool = False,
) -> Optional[dict[str, Any]]:
    """
    キャッシュがなければ LINE API からプロフィールを取得して保存する。
    force_refresh=True で常に再取得。
    """
    if not user_id:
        return None

    existing = session.get("line_profile") if hasattr(session, "get") else None
    if isinstance(existing, dict) and existing and not force_refresh:
        display = (existing.get("displayName") or "").strip()
        if display and str(session.get("username", "")).startswith("LINEユーザー"):
            session["username"] = display
        sync_language_from_line_profile(session)
        return existing

    if sid and not force_refresh:
        if is_line_session_id(sid):
            stored = get_session_from_memory(sid) or {}
        else:
            stored = get_session_from_db(sid) or {}
        stored_profile = stored.get("line_profile")
        if isinstance(stored_profile, dict) and stored_profile.get("displayName"):
            session["line_profile"] = stored_profile
            session["username"] = stored_profile.get("displayName") or session.get("username")
            sync_language_from_line_profile(session, stored)
            return stored_profile

    from src.services.pipeline_perf import mark_pipeline_step

    mark_pipeline_step("line_profile_fetch")
    profile = await fetch_line_user_profile(user_id)
    if profile:
        apply_line_profile_to_session(session, profile, sid=sid)
        return profile

    err = "token_not_configured" if not get_line_channel_access_token() else "profile_fetch_failed"
    if sid:
        if is_line_session_id(sid):
            session_data = get_session_from_memory(sid) or {"session_id": sid}
        else:
            session_data = get_session_from_db(sid) or {"session_id": sid}
        append_lifecycle_event(
            session_data,
            "profile_fetch_failed",
            source="line_profile.ensure_line_user_profile",
            detail=f"userId={user_id}; reason={err}",
        )
        session_data["line_profile_error"] = err
        save_session_to_db(sid, session_data)
        if hasattr(session, "__setitem__"):
            session["line_profile_error"] = err
    return None


async def refresh_line_profile_by_session_id(session_id: str, *, force: bool = True) -> dict[str, Any]:
    """管理画面用: session_id からプロフィールを再取得。"""
    session_id = normalize_line_session_id(session_id) or session_id
    user_id = user_id_from_line_sid(session_id)
    if not user_id:
        return {"ok": False, "error": "not_a_line_session"}

    if not get_line_channel_access_token():
        return {"ok": False, "error": "token_not_configured"}

    session_data = get_session_from_db(session_id)
    if not session_data:
        session_data = {
            "session_id": session_id,
            "messages": [],
            "username": f"LINEユーザー{user_id[-6:]}",
        }

    profile = await ensure_line_user_profile(
        user_id,
        session_data,
        sid=session_id,
        force_refresh=force,
    )
    if not profile:
        return {"ok": False, "error": "profile_fetch_failed", "line_profile": session_data.get("line_profile")}
    return {"ok": True, "line_profile": profile, "username": session_data.get("username")}
