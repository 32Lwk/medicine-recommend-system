"""チャット/LINE パイプラインのステップ計測（sid キー + ワーカースレッド対応）。"""
from __future__ import annotations

import logging
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_PIPELINE_PERF_WARN_MS = 10_000.0

_active_sid: ContextVar[str | None] = ContextVar("pipeline_perf_active_sid", default=None)

# sync-only / sid なしフォールバック
_channel: ContextVar[str] = ContextVar("pipeline_perf_channel", default="web")
_steps: ContextVar[dict[str, float] | None] = ContextVar("pipeline_perf_steps", default=None)
_started: ContextVar[float | None] = ContextVar("pipeline_perf_started", default=None)
_extra: ContextVar[dict[str, Any] | None] = ContextVar("pipeline_perf_extra", default=None)


@dataclass
class _PerfBucket:
    channel: str = "web"
    started: float = 0.0
    steps: dict[str, float] = field(default_factory=dict)
    llm_calls: list[dict[str, Any]] = field(default_factory=list)
    llm_session_cost_jpy: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


_lock = threading.Lock()
_buckets: dict[str, _PerfBucket] = {}


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _bucket_for(sid: str | None = None) -> _PerfBucket | None:
    key = sid or _active_sid.get()
    if not key:
        return None
    with _lock:
        return _buckets.get(key)


def bind_pipeline_perf(*, sid: str, channel: str = "web", reset: bool = False) -> None:
    """リクエスト開始時に sid 単位の計測バケットを確保する。"""
    if not sid:
        return
    with _lock:
        if sid in _buckets and not reset:
            _active_sid.set(sid)
            return
        _buckets[sid] = _PerfBucket(channel=channel, started=time.perf_counter())
    _active_sid.set(sid)


def activate_pipeline_perf(sid: str | None) -> None:
    """ワーカースレッド内で active sid を設定する（bind 済みバケットを参照）。"""
    if sid:
        _active_sid.set(sid)


def start_pipeline_perf(*, channel: str = "web", sid: str | None = None) -> None:
    if sid:
        bind_pipeline_perf(sid=sid, channel=channel)
        return
    _channel.set(channel)
    _steps.set({})
    _started.set(time.perf_counter())
    _extra.set({})


def ensure_pipeline_perf_started(*, channel: str = "web", sid: str | None = None) -> None:
    """計測が未開始なら開始（LINE handler から既に bind 済みの場合は sid のみ同期）。"""
    sid = sid or _active_sid.get()
    if sid:
        if _bucket_for(sid) is None:
            bind_pipeline_perf(sid=sid, channel=channel)
        else:
            activate_pipeline_perf(sid)
        return
    if _steps.get() is None:
        start_pipeline_perf(channel=channel)


def mark_pipeline_step(step: str) -> None:
    bucket = _bucket_for()
    if bucket is not None:
        bucket.steps[step] = _elapsed_ms(bucket.started)
        return
    steps = _steps.get()
    if steps is None:
        return
    steps[step] = _elapsed_ms(_started.get() or time.perf_counter())


def record_pipeline_perf(**fields: Any) -> None:
    """PIPELINE_PERF ログに載せる追加フィールド（delivery_mode 等）。"""
    if not fields:
        return
    bucket = _bucket_for()
    if bucket is not None:
        bucket.extra.update(fields)
        return
    extra = _extra.get()
    if extra is None:
        extra = {}
        _extra.set(extra)
    extra.update(fields)


def append_llm_call_to_bucket(entry: dict[str, Any], *, cost_jpy: float = 0.0) -> bool:
    bucket = _bucket_for()
    if bucket is None:
        return False
    bucket.llm_calls.append(entry)
    if cost_jpy:
        bucket.llm_session_cost_jpy += cost_jpy
    return True


def reset_llm_calls_in_bucket() -> bool:
    bucket = _bucket_for()
    if bucket is None:
        return False
    bucket.llm_calls.clear()
    bucket.llm_session_cost_jpy = 0.0
    return True


def get_active_bucket_llm_calls() -> list[dict[str, Any]] | None:
    bucket = _bucket_for()
    if bucket is None:
        return None
    return list(bucket.llm_calls)


def get_active_bucket_llm_cost_jpy() -> float | None:
    bucket = _bucket_for()
    if bucket is None:
        return None
    return bucket.llm_session_cost_jpy


def get_active_bucket_llm_summary() -> dict[str, Any] | None:
    bucket = _bucket_for()
    if bucket is None:
        return None
    return _llm_summary_from_bucket(bucket)


def _llm_summary_from_bucket(bucket: _PerfBucket) -> dict[str, Any]:
    calls = list(bucket.llm_calls)
    try:
        from config.llm_config import LLM_MODEL_PROFILE

        profile = LLM_MODEL_PROFILE
    except ImportError:
        profile = "gpt5"
    return {
        "llm_calls": calls,
        "llm_call_count": len(calls),
        "llm_total_latency_ms": sum(c.get("latency_ms", 0) for c in calls),
        "llm_session_cost_jpy": round(bucket.llm_session_cost_jpy, 4),
        "model_profile": profile,
    }


def _pop_bucket(sid: str | None) -> _PerfBucket | None:
    if not sid:
        return _bucket_for()
    with _lock:
        return _buckets.pop(sid, None)


def log_pipeline_perf(*, sid: str | None = None, extra: dict[str, Any] | None = None) -> None:
    bucket = _pop_bucket(sid) if sid else None
    if bucket is None:
        bucket = _pop_bucket(_active_sid.get())
    if bucket is not None:
        total_ms = _elapsed_ms(bucket.started)
        payload: dict[str, Any] = {
            "channel": bucket.channel,
            "sid": sid or _active_sid.get() or "",
            "total_ms": total_ms,
            "breakdown": dict(bucket.steps),
            "llm": _llm_summary_from_bucket(bucket),
        }
        if bucket.extra:
            payload.update(bucket.extra)
        if extra:
            payload.update(extra)
        log_fn = logger.warning if total_ms >= _PIPELINE_PERF_WARN_MS else logger.info
        log_fn("PIPELINE_PERF %s", payload)
        return

    steps = _steps.get() or {}
    started = _started.get()
    total_ms = _elapsed_ms(started) if started else 0.0
    channel = _channel.get()
    payload = {
        "channel": channel,
        "sid": sid or "",
        "total_ms": total_ms,
        "breakdown": dict(steps),
    }
    fallback_extra = _extra.get()
    if fallback_extra:
        payload.update(fallback_extra)
    if extra:
        payload.update(extra)
    try:
        from src.services.llm_metrics import get_llm_summary

        payload["llm"] = get_llm_summary()
    except Exception:
        pass
    log_fn = logger.warning if total_ms >= _PIPELINE_PERF_WARN_MS else logger.info
    log_fn("PIPELINE_PERF %s", payload)
