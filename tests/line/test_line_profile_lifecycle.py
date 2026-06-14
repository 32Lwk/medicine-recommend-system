"""session_lifecycle と LINE プロフィールのテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_profile import fetch_line_user_profile, ensure_line_user_profile
from src.services.session_lifecycle import (
    admin_messages_for_session,
    append_lifecycle_event,
    ensure_line_session_archive,
    merge_messages_into_archive,
)


def test_merge_messages_into_archive_dedupes():
    data = {"message_archive": [{"type": "user", "content": "a", "uuid": "u1"}]}
    added = merge_messages_into_archive(data, [
        {"type": "user", "content": "a", "uuid": "u1"},
        {"type": "bot", "content": "b", "uuid": "u2"},
    ])
    assert added == 1
    assert len(data["message_archive"]) == 2


def test_admin_messages_merges_archive_and_live():
    info = {
        "messages": [{"type": "user", "content": "new", "uuid": "u2"}],
        "message_archive": [{"type": "user", "content": "old", "uuid": "u1"}],
    }
    msgs = admin_messages_for_session(info)
    assert len(msgs) == 2


def test_ensure_line_session_archive_backfills_from_messages():
    info = {"messages": [{"type": "user", "content": "a", "uuid": "x1"}]}
    assert ensure_line_session_archive(info) is True
    assert len(info["message_archive"]) == 1


def test_append_lifecycle_event():
    data = {}
    append_lifecycle_event(data, "message_trim", detail="test", messages_before=10, messages_after=5)
    assert len(data["lifecycle_log"]) == 1
    assert data["lifecycle_log"][0]["action"] == "message_trim"


def test_fetch_line_user_profile_parses_all_fields():
    async def _run():
        with patch(
            "src.handlers.line.line_profile.get_json",
            new_callable=AsyncMock,
            return_value={
                "userId": "Uabc",
                "displayName": "太郎",
                "pictureUrl": "https://example.com/p.png",
                "statusMessage": "hello",
                "language": "ja",
            },
        ), patch("src.handlers.line.line_profile.get_line_channel_access_token", return_value="tok"):
            return await fetch_line_user_profile("Uabc")

    profile = asyncio.run(_run())
    assert profile["displayName"] == "太郎"
    assert profile["pictureUrl"] == "https://example.com/p.png"
    assert profile["fetched_at"]


def test_ensure_line_user_profile_updates_username():
    from src.services.session_manager import touch_session_in_memory

    sid = "line:Uprof1"
    touch_session_in_memory(sid, {"session_id": sid, "messages": [], "username": "LINEユーザーprof1"})
    session = {"username": "LINEユーザーprof1"}

    async def _run():
        with patch(
            "src.handlers.line.line_profile.fetch_line_user_profile",
            new_callable=AsyncMock,
            return_value={
                "userId": "Uprof1",
                "displayName": "花子",
                "language": "ja",
                "fetched_at": "2026-01-01T00:00:00",
            },
        ):
            return await ensure_line_user_profile("Uprof1", session, sid=sid)

    asyncio.run(_run())
    assert session["username"] == "花子"
    assert session["line_profile"]["displayName"] == "花子"


def test_apply_line_profile_clears_stale_error_and_skips_duplicate_lifecycle():
    from src.handlers.line.line_profile import apply_line_profile_to_session

    sid = "line:Udup1"
    session_data = {
        "session_id": sid,
        "messages": [],
        "username": "LINEユーザーdup1",
        "line_profile_error": "token_not_configured",
        "line_profile": {"displayName": "宥翔", "userId": "Udup1"},
        "lifecycle_log": [],
    }
    with patch("src.handlers.line.line_profile.save_session_to_db"), patch(
        "src.handlers.line.line_profile.touch_session_in_memory"
    ), patch(
        "src.handlers.line.line_profile.get_session_from_db",
        return_value=dict(session_data),
    ):
        apply_line_profile_to_session(
            session_data,
            {
                "userId": "Udup1",
                "displayName": "宥翔",
                "fetched_at": "2026-06-15T00:00:00",
            },
            sid=sid,
        )
    assert "line_profile_error" not in session_data
    assert session_data.get("lifecycle_log") == []
