"""管理画面からの LINE 手動返信。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

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
