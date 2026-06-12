"""LINE ローディングアニメーションの維持（最大60秒制限への対応）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from config.line_config import LINE_CHANNEL_ACCESS_TOKEN
from src.handlers.line.line_reply import start_loading_animation

logger = logging.getLogger(__name__)

# LINE API の上限 60 秒の少し手前で再発火する
_KEEPALIVE_INTERVAL_SEC = 50.0


async def begin_line_loading(user_id: str) -> tuple[asyncio.Event, asyncio.Task[Any] | None]:
    """
    loading/start を即 await してから keepalive を開始する。
    同期処理（DB 読込等）より先に LINE へリクエストを送る。
    戻り値は end_line_loading で必ず片付ける。
    """
    stop = asyncio.Event()
    if not user_id or not LINE_CHANNEL_ACCESS_TOKEN:
        return stop, None
    await start_loading_animation(user_id)
    keepalive_task = asyncio.create_task(run_loading_keepalive(user_id, stop))
    return stop, keepalive_task


async def end_line_loading(
    stop: asyncio.Event,
    keepalive_task: asyncio.Task[Any] | None,
) -> None:
    stop.set()
    if keepalive_task is not None:
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass


async def run_loading_keepalive(user_id: str, stop: asyncio.Event) -> None:
    """
    長時間処理中も「…」表示を維持する。
    初回は begin_line_loading が dispatch 済みのため、ここでは期限前の再発火のみ行う。
    """
    if not user_id:
        return
    try:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=_KEEPALIVE_INTERVAL_SEC)
                return
            except asyncio.TimeoutError:
                await start_loading_animation(user_id)
                logger.debug("LINE loading keepalive refresh userId=%s", user_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("LINE loading keepalive error userId=%s", user_id)
