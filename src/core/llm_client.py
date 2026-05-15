"""
OpenAI Chat Completions / Responses API 統一ラッパ（同期・非同期・計測・予算チェック）
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from config.llm_config import get_model, get_openai_api_key, use_responses_api
from src.services.budget_guard import check_llm_allowed

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm_async")

_COST_PER_1K: Dict[str, float] = {
    "gpt-4o-mini": 0.03,
    "gpt-4o": 0.15,
    "gpt-4": 0.15,
    "gpt-5.4-mini": 0.03,
    "gpt-5.5": 0.20,
}


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message


@dataclass
class _CompletionAdapter:
    """Chat Completions 互換の薄いラッパ（Responses API 用）"""
    choices: List[_Choice]
    usage: Any


def _estimate_cost_jpy(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = _COST_PER_1K.get(model, 0.05)
    return (prompt_tokens + completion_tokens) / 1000.0 * rate


def _record_response(model: str, path: str, latency_ms: float, response: Any) -> None:
    from src.services.llm_metrics import record_llm_call
    from src.services.budget_guard import add_monthly_cost

    usage = getattr(response, "usage", None)
    pt = int(getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0)
    cost = _estimate_cost_jpy(model, pt, ct)
    record_llm_call(
        model=model,
        path=path,
        latency_ms=latency_ms,
        prompt_tokens=pt,
        completion_tokens=ct,
        cost_jpy=cost,
        prompt_version="responses" if use_responses_api() else "completions",
    )
    if cost > 0:
        add_monthly_cost(cost)


def _budget_guard_or_raise():
    allowed, reason = check_llm_allowed()
    if not allowed:
        raise RuntimeError(reason or "llm_budget_blocked")


def _extract_responses_text(resp: Any) -> str:
    if getattr(resp, "output_text", None):
        return resp.output_text
    parts: List[str] = []
    for item in getattr(resp, "output", None) or []:
        if getattr(item, "type", None) == "message":
            for block in getattr(item, "content", None) or []:
                if getattr(block, "type", None) == "output_text":
                    parts.append(getattr(block, "text", "") or "")
    return "".join(parts)


def _responses_create(client: OpenAI, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> _CompletionAdapter:
    req: Dict[str, Any] = {"model": model, "input": messages}
    if "max_tokens" in kwargs:
        req["max_output_tokens"] = kwargs.pop("max_tokens")
    if "temperature" in kwargs:
        req["temperature"] = kwargs["temperature"]
    rf = kwargs.pop("response_format", None)
    if rf and rf.get("type") == "json_object":
        req["text"] = {"format": {"type": "json_object"}}
    req.update({k: v for k, v in kwargs.items() if k not in ("model", "messages")})

    resp = client.responses.create(**req)
    text = _extract_responses_text(resp)
    return _CompletionAdapter(choices=[_Choice(message=_Message(content=text))], usage=resp.usage)


def _invoke_llm(
    client: OpenAI,
    *,
    model: str,
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Any:
    if use_responses_api():
        try:
            return _responses_create(client, model, messages, **kwargs)
        except Exception as e:
            logger.warning("Responses API failed, fallback to Chat Completions: %s", e)
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def chat_completion_create(
    client: OpenAI,
    *,
    model_role: str,
    path: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    _budget_guard_or_raise()
    resolved = model or get_model(model_role)
    t0 = time.time()
    response = _invoke_llm(client, model=resolved, messages=messages, **kwargs)
    _record_response(resolved, path, (time.time() - t0) * 1000, response)
    return response


async def _invoke_llm_async(
    async_client: AsyncOpenAI,
    *,
    model: str,
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Any:
    if use_responses_api():
        try:
            req: Dict[str, Any] = {"model": model, "input": messages}
            if "max_tokens" in kwargs:
                req["max_output_tokens"] = kwargs.pop("max_tokens")
            if "temperature" in kwargs:
                req["temperature"] = kwargs["temperature"]
            rf = kwargs.pop("response_format", None)
            if rf and rf.get("type") == "json_object":
                req["text"] = {"format": {"type": "json_object"}}
            resp = await async_client.responses.create(**req)
            text = _extract_responses_text(resp)
            return _CompletionAdapter(choices=[_Choice(message=_Message(content=text))], usage=resp.usage)
        except Exception as e:
            logger.warning("Async Responses API failed, fallback: %s", e)
    return await async_client.chat.completions.create(model=model, messages=messages, **kwargs)


async def chat_completion_create_async(
    async_client: AsyncOpenAI,
    *,
    model_role: str,
    path: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    _budget_guard_or_raise()
    resolved = model or get_model(model_role)
    t0 = time.time()
    response = await _invoke_llm_async(async_client, model=resolved, messages=messages, **kwargs)
    _record_response(resolved, path, (time.time() - t0) * 1000, response)
    return response


def get_async_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    key = api_key or get_openai_api_key()
    if not key:
        raise ValueError("OPENAI_API_KEY not configured")
    return AsyncOpenAI(api_key=key)


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    future = _executor.submit(asyncio.run, coro)
    return future.result()


async def gather_llm_tasks(*coros):
    return await asyncio.gather(*coros, return_exceptions=True)
