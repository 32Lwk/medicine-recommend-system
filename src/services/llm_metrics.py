"""
リクエスト単位の LLM 呼び出しメトリクス（access_analytics 連携用）
"""
from __future__ import annotations

import contextvars
from datetime import datetime
from typing import Any, Dict, List, Optional

_llm_calls_var: contextvars.ContextVar[Optional[List[Dict[str, Any]]]] = contextvars.ContextVar(
    "llm_calls", default=None
)
_session_cost_var: contextvars.ContextVar[float] = contextvars.ContextVar(
    "llm_session_cost_jpy", default=0.0
)


def reset_llm_metrics() -> None:
    _llm_calls_var.set([])
    _session_cost_var.set(0.0)


def record_llm_call(
    *,
    model: str,
    path: str,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_jpy: float = 0.0,
    profile: str | None = None,
    prompt_version: str | None = None,
) -> None:
    calls = _llm_calls_var.get()
    if calls is None:
        calls = []
        _llm_calls_var.set(calls)
    entry: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "path": path,
        "latency_ms": round(latency_ms, 2),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_jpy": round(cost_jpy, 4),
    }
    if profile:
        entry["model_profile"] = profile
    if prompt_version:
        entry["prompt_version"] = prompt_version
    calls.append(entry)
    if cost_jpy:
        _session_cost_var.set(_session_cost_var.get() + cost_jpy)


def get_llm_calls() -> List[Dict[str, Any]]:
    return list(_llm_calls_var.get() or [])


def get_session_cost_jpy() -> float:
    return _session_cost_var.get()


def get_llm_summary() -> Dict[str, Any]:
    calls = get_llm_calls()
    try:
        from config.llm_config import LLM_MODEL_PROFILE
        profile = LLM_MODEL_PROFILE
    except ImportError:
        profile = "gpt5"
    return {
        "llm_calls": calls,
        "llm_call_count": len(calls),
        "llm_total_latency_ms": sum(c.get("latency_ms", 0) for c in calls),
        "llm_session_cost_jpy": round(get_session_cost_jpy(), 4),
        "model_profile": profile,
    }


def merge_into_user_info(user_info: Optional[Dict]) -> Dict:
    base = dict(user_info or {})
    base.update(get_llm_summary())
    return base
