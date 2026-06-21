"""管理画面からの LINE 手動返信。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from datetime import datetime

from src.handlers.line.line_admin_manual_reply import apply_admin_manual_reply
from src.services.session_manager import touch_session_in_memory


def test_apply_admin_manual_reply_pushes_to_line():
    sid = "line:Utest123"
    touch_session_in_memory(sid, {"session_id": sid, "messages": [], "username": "LINEユーザー"})

    async def _run():
        with (
            patch(
                "src.handlers.line.line_admin_manual_reply.push_messages",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
            patch(
                "src.handlers.line.line_admin_manual_reply.get_line_channel_access_token",
                return_value="test-token",
            ),
        ):
            return await apply_admin_manual_reply(sid, "薬剤師からの返信です"), mock_push

    result, mock_push = asyncio.run(_run())

    assert result["ok"] is True
    assert result["line_pushed"] is True
    assert result.get("line_error") is None
    mock_push.assert_awaited_once_with(
        "Utest123",
        [{"type": "text", "text": "薬剤師からの返信です"}],
    )


def test_apply_admin_manual_reply_web_session_skips_line_push():
    sid = "web-session-1"
    touch_session_in_memory(sid, {"session_id": sid, "messages": [], "username": "ユーザー1"})

    async def _run():
        with patch(
            "src.handlers.line.line_admin_manual_reply.push_messages",
            new_callable=AsyncMock,
        ) as mock_push:
            result = await apply_admin_manual_reply(sid, "通常の返信")
            return result, mock_push

    result, mock_push = asyncio.run(_run())

    assert result["ok"] is True
    assert result["line_pushed"] is None
    mock_push.assert_not_awaited()


def test_apply_admin_manual_reply_line_without_token():
    sid = "line:Utest456"
    touch_session_in_memory(sid, {"session_id": sid, "messages": [], "username": "LINEユーザー"})

    async def _run():
        with (
            patch(
                "src.handlers.line.line_admin_manual_reply.push_messages",
                new_callable=AsyncMock,
            ) as mock_push,
            patch(
                "src.handlers.line.line_admin_manual_reply.get_line_channel_access_token",
                return_value="",
            ),
        ):
            result = await apply_admin_manual_reply(sid, "返信")
            return result, mock_push

    result, mock_push = asyncio.run(_run())

    assert result["ok"] is True
    assert result["line_pushed"] is False
    assert result["line_error"] == "LINE_CHANNEL_ACCESS_TOKEN not configured"
    mock_push.assert_not_awaited()


def test_apply_admin_manual_reply_persists_before_clearing_admin_request():
    sid = "line:Upersist789"
    stored: dict = {
        "session_id": sid,
        "messages": [],
        "username": "LINEユーザー",
        "admin_request": True,
        "last_activity": datetime(2026, 6, 21, 19, 36, 32),
    }
    touch_session_in_memory(sid, dict(stored))
    save_calls: list[dict] = []

    def _fake_get_session(session_id):
        if session_id != sid:
            return None
        return dict(stored)

    def _fake_save(session_id, data):
        stored.clear()
        stored.update(data)
        save_calls.append(dict(data))
        return True

    async def _run():
        with (
            patch(
                "src.handlers.line.line_admin_manual_reply.get_session_from_db",
                side_effect=_fake_get_session,
            ),
            patch(
                "src.handlers.line.line_admin_request.get_session_from_db",
                side_effect=_fake_get_session,
            ),
            patch(
                "src.handlers.line.line_admin_manual_reply.save_session_to_db",
                side_effect=_fake_save,
            ),
            patch(
                "src.handlers.line.line_admin_request.save_session_to_db",
                side_effect=_fake_save,
            ),
            patch(
                "src.handlers.line.line_admin_request.get_manual_reply_queue",
                return_value=[{"session_id": sid, "admin_request": True}],
            ),
            patch("src.handlers.line.line_admin_request.set_manual_reply_queue"),
            patch(
                "src.handlers.line.line_admin_manual_reply.push_messages",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.handlers.line.line_admin_manual_reply.get_line_channel_access_token",
                return_value="test-token",
            ),
        ):
            return await apply_admin_manual_reply(sid, "手動返信テスト")

    result = asyncio.run(_run())

    assert result["ok"] is True
    assert len(stored.get("messages") or []) == 1
    assert stored["messages"][0]["manual_reply"] is True
    assert stored.get("admin_request") is None
    assert isinstance(stored["last_activity"], datetime)
    assert len(save_calls) >= 2
    first_save_msgs = save_calls[0].get("messages") or []
    assert first_save_msgs and first_save_msgs[0]["content"] == "手動返信テスト"
