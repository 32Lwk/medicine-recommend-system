"""LINE loading keepalive のテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.handlers.line.line_loading import run_loading_keepalive


@patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock)
def test_loading_keepalive_refreshes_before_stop(mock_start):
    async def _run():
        stop = asyncio.Event()
        task = asyncio.create_task(run_loading_keepalive("U1", stop))
        await asyncio.sleep(0.05)
        stop.set()
        await task

    asyncio.run(_run())
    mock_start.assert_awaited()


@patch("src.handlers.line.line_loading.start_loading_animation", new_callable=AsyncMock)
def test_loading_keepalive_rerequests_on_interval(mock_start):
    async def _run():
        stop = asyncio.Event()
        with patch("src.handlers.line.line_loading._KEEPALIVE_INTERVAL_SEC", 0.02):
            task = asyncio.create_task(run_loading_keepalive("U1", stop))
            await asyncio.sleep(0.06)
            stop.set()
            await task

    asyncio.run(_run())
    assert mock_start.await_count >= 2
