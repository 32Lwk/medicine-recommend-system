"""LINE ローディングアニメーションの維持（最大60秒制限への対応）。"""
from __future__ import annotations

import asyncio
import logging

from src.handlers.line.line_reply import start_loading_animation

logger = logging.getLogger(__name__)

# LINE API の上限 60 秒の少し手前で再発火する
_KEEPALIVE_INTERVAL_SEC = 50.0


async def run_loading_keepalive(user_id: str, stop: asyncio.Event) -> None:
    """
    長時間処理中も「…」表示を維持する。
    loading/start は最大60秒で切れるため、期限前に再発火する。
    """
    if not user_id:
        return
    try:
        while not stop.is_set():
            await start_loading_animation(user_id)
            try:
                await asyncio.wait_for(stop.wait(), timeout=_KEEPALIVE_INTERVAL_SEC)
                return
            except asyncio.TimeoutError:
                logger.debug("LINE loading keepalive refresh userId=%s", user_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("LINE loading keepalive error userId=%s", user_id)
