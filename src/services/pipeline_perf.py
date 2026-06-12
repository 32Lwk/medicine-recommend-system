"""チャット/LINE パイプラインのステップ計測（contextvars）。"""
from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

_channel: ContextVar[str] = ContextVar("pipeline_perf_channel", default="web")
_steps: ContextVar[dict[str, float] | None] = ContextVar("pipeline_perf_steps", default=None)
_started: ContextVar[float | None] = ContextVar("pipeline_perf_started", default=None)


def start_pipeline_perf(*, channel: str = "web") -> None:
    _channel.set(channel)
    _steps.set({})
    _started.set(time.perf_counter())


def ensure_pipeline_perf_started(*, channel: str = "web") -> None:
    """計測が未開始なら開始（LINE handler から既に開始済みの場合は no-op）。"""
    if _steps.get() is None:
        start_pipeline_perf(channel=channel)


def mark_pipeline_step(step: str) -> None:
    steps = _steps.get()
    if steps is None:
        return
    steps[step] = round((time.perf_counter() - (_started.get() or time.perf_counter())) * 1000, 2)


def log_pipeline_perf(*, sid: str | None = None, extra: dict[str, Any] | None = None) -> None:
    steps = _steps.get() or {}
    started = _started.get()
    total_ms = round((time.perf_counter() - started) * 1000, 2) if started else 0.0
    channel = _channel.get()
    payload: dict[str, Any] = {
        "channel": channel,
        "sid": sid or "",
        "total_ms": total_ms,
        "breakdown": steps,
    }
    if extra:
        payload.update(extra)
    try:
        from src.services.llm_metrics import get_llm_summary

        payload["llm"] = get_llm_summary()
    except Exception:
        pass
    logger.info("PIPELINE_PERF %s", payload)
