"""
OpenAI Chat Completions / Responses API 統一ラッパ（同期・非同期・計測・予算チェック）
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from config.llm_config import (
    get_model,
    get_openai_api_key,
    get_role_timeout_sec,
    use_responses_api,
    use_responses_api_for_role,
)
from src.services.budget_guard import check_llm_allowed

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="llm_async")

_COST_PER_1K: Dict[str, float] = {
    "gpt-4o-mini": 0.03,
    "gpt-4o": 0.15,
    "gpt-4": 0.15,
    "gpt-5.4-mini": 0.03,
    "gpt-5.4": 0.12,
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


def text_completion_adapter(text: str) -> _CompletionAdapter:
    return _CompletionAdapter(choices=[_Choice(message=_Message(content=text))], usage=None)


def _estimate_cost_jpy(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = _COST_PER_1K.get(model, 0.05)
    return (prompt_tokens + completion_tokens) / 1000.0 * rate


def _record_response(
    model: str,
    path: str,
    latency_ms: float,
    response: Any,
    *,
    api_kind: Optional[str] = None,
) -> None:
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
        prompt_version=api_kind or ("responses" if use_responses_api() else "completions"),
    )
    if cost > 0:
        add_monthly_cost(cost)


def _budget_guard_or_raise():
    allowed, reason = check_llm_allowed()
    if not allowed:
        raise RuntimeError(reason or "llm_budget_blocked")


def _uses_max_completion_tokens(model: str) -> bool:
    """gpt-5 / o 系は Chat Completions で max_tokens 非対応のことがある。"""
    name = (model or "").strip().lower()
    if not name:
        return False
    if name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3") or name.startswith("o4"):
        return True
    return False


def _supports_custom_temperature(model: str) -> bool:
    """gpt-5 / o 系は temperature カスタム値非対応（既定 1 のみ）。"""
    name = (model or "").strip().lower()
    if not name:
        return True
    if name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3") or name.startswith("o4"):
        return False
    return True


def extract_completion_text(response: Any) -> str:
    """Chat Completions / Responses ラッパから本文を取り出す（空・拒否応答に耐える）。"""
    if response is None:
        return ""
    try:
        choices = getattr(response, "choices", None) or []
        if choices:
            msg = getattr(choices[0], "message", None)
            if msg is not None:
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    return content.strip()
                refusal = getattr(msg, "refusal", None)
                if isinstance(refusal, str) and refusal.strip():
                    return refusal.strip()
    except Exception:
        pass
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


_LLM_INTERNAL_KWARGS = frozenset({"session_id", "on_delta"})


def _prepare_chat_completion_kwargs(model: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Chat Completions 向けにトークン上限・temperature を正規化する。"""
    prepared = {k: v for k, v in kwargs.items() if k not in _LLM_INTERNAL_KWARGS}
    # Chat Completions API は reasoning_effort 非対応（Responses API 専用）
    prepared.pop("reasoning_effort", None)
    if "max_tokens" in prepared and _uses_max_completion_tokens(model):
        prepared["max_completion_tokens"] = prepared.pop("max_tokens")
    if not _supports_custom_temperature(model) and "temperature" in prepared:
        prepared.pop("temperature")
    return prepared


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
    reasoning_effort = kwargs.pop("reasoning_effort", None)
    kwargs = _prepare_chat_completion_kwargs(model, kwargs)
    req: Dict[str, Any] = {"model": model, "input": messages}
    if "max_tokens" in kwargs:
        req["max_output_tokens"] = kwargs.pop("max_tokens")
    if "max_completion_tokens" in kwargs:
        req["max_output_tokens"] = kwargs.pop("max_completion_tokens")
    if "temperature" in kwargs:
        req["temperature"] = kwargs["temperature"]
    if reasoning_effort:
        req["reasoning"] = {"effort": reasoning_effort}
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
    model_role: Optional[str] = None,
    force_chat_completions: bool = False,
    **kwargs: Any,
) -> tuple[Any, str]:
    use_resp = (
        not force_chat_completions
        and hasattr(client, "responses")
        and (
            use_responses_api()
            or (model_role is not None and use_responses_api_for_role(model_role))
        )
    )
    if model_role:
        kwargs.setdefault("timeout", get_role_timeout_sec(model_role))
    if use_resp:
        try:
            return _responses_create(client, model, messages, **kwargs), "responses"
        except Exception as e:
            logger.warning(
                "Responses API failed, fallback to Chat Completions: role=%s model=%s err=%s",
                model_role,
                model,
                e,
            )
    chat_kwargs = _prepare_chat_completion_kwargs(model, kwargs)
    return client.chat.completions.create(model=model, messages=messages, **chat_kwargs), "completions"


def chat_completion_create(
    client: OpenAI,
    *,
    model_role: str,
    path: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    force_chat_completions: bool = False,
    **kwargs: Any,
) -> Any:
    _budget_guard_or_raise()
    resolved = model or get_model(model_role)
    t0 = time.time()
    response, api_kind = _invoke_llm(
        client,
        model=resolved,
        messages=messages,
        model_role=model_role,
        force_chat_completions=force_chat_completions,
        **kwargs,
    )
    _record_response(resolved, path, (time.time() - t0) * 1000, response, api_kind=api_kind)
    return response


def chat_completion_stream(
    client: OpenAI,
    *,
    model_role: str,
    path: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    on_delta: Optional[Callable[[str], None]] = None,
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Chat Completions ストリーミング（自然文アドバイス用）。
    Responses API ロールは非ストリームの completions にフォールバック。
    """
    _budget_guard_or_raise()
    resolved = model or get_model(model_role)
    if use_responses_api_for_role(model_role):
        response = chat_completion_create(
            client,
            model_role=model_role,
            path=path,
            messages=messages,
            model=model,
            **kwargs,
        )
        text = response.choices[0].message.content or ""
        if on_delta and text:
            on_delta(text)
        elif session_id and text:
            from src.services.sse_emit import emit_advice_delta, reply_stream_sse_enabled

            if reply_stream_sse_enabled():
                emit_advice_delta(text, session_id)
        return text

    stream_kwargs = dict(kwargs)
    stream_kwargs.pop("response_format", None)
    if model_role:
        stream_kwargs.setdefault("timeout", get_role_timeout_sec(model_role))
    stream_kwargs = _prepare_chat_completion_kwargs(resolved, stream_kwargs)

    t0 = time.time()
    parts: List[str] = []
    stream = client.chat.completions.create(
        model=resolved,
        messages=messages,
        stream=True,
        **stream_kwargs,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        parts.append(delta)
        if on_delta:
            on_delta(delta)
        elif session_id:
            from src.services.sse_emit import emit_advice_delta, reply_stream_sse_enabled

            if reply_stream_sse_enabled():
                emit_advice_delta(delta, session_id)

    text = "".join(parts)
    pt_est = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
    ct_est = max(1, len(text) // 4)
    cost = _estimate_cost_jpy(resolved, pt_est, ct_est)
    from src.services.llm_metrics import record_llm_call

    record_llm_call(
        model=resolved,
        path=path,
        latency_ms=(time.time() - t0) * 1000,
        prompt_tokens=pt_est,
        completion_tokens=ct_est,
        cost_jpy=cost,
        prompt_version="completions_stream",
    )
    if cost > 0:
        from src.services.budget_guard import add_monthly_cost

        add_monthly_cost(cost)
    return text


def responses_stream(
    client: OpenAI,
    *,
    model_role: str,
    path: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    on_delta: Optional[Callable[[str], None]] = None,
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Responses API ストリーミング（未対応時は一括生成＋疑似デルタ）"""
    if not use_responses_api_for_role(model_role):
        return chat_completion_stream(
            client,
            model_role=model_role,
            path=path,
            messages=messages,
            model=model,
            on_delta=on_delta,
            session_id=session_id,
            **kwargs,
        )

    _budget_guard_or_raise()
    resolved = model or get_model(model_role)
    req: Dict[str, Any] = {"model": resolved, "input": messages, "stream": True}
    if "max_tokens" in kwargs:
        req["max_output_tokens"] = kwargs.pop("max_tokens")
    if model_role:
        kwargs.setdefault("timeout", get_role_timeout_sec(model_role))

    t0 = time.time()
    parts: List[str] = []
    try:
        stream = client.responses.create(**req)
        for event in stream:
            delta = getattr(event, "delta", None) or ""
            if not delta and hasattr(event, "type"):
                if getattr(event, "type", "") == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
            if delta:
                parts.append(delta)
                if on_delta:
                    on_delta(delta)
                elif session_id:
                    from src.services.sse_emit import emit_advice_delta, reply_stream_sse_enabled

                    if reply_stream_sse_enabled():
                        emit_advice_delta(delta, session_id)
    except Exception as e:
        logger.warning("responses_stream fallback to batch: %s", e)
        return chat_completion_stream(
            client,
            model_role=model_role,
            path=path,
            messages=messages,
            model=model,
            on_delta=on_delta,
            session_id=session_id,
            **kwargs,
        )

    text = "".join(parts)
    pt_est = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
    ct_est = max(1, len(text) // 4)
    from src.services.llm_metrics import record_llm_call

    record_llm_call(
        model=resolved,
        path=path,
        latency_ms=(time.time() - t0) * 1000,
        prompt_tokens=pt_est,
        completion_tokens=ct_est,
        cost_jpy=_estimate_cost_jpy(resolved, pt_est, ct_est),
        prompt_version="responses_stream",
    )
    return text


async def _invoke_llm_async(
    async_client: AsyncOpenAI,
    *,
    model: str,
    messages: List[Dict[str, str]],
    model_role: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    use_resp = (
        hasattr(async_client, "responses")
        and (
            use_responses_api()
            or (model_role is not None and use_responses_api_for_role(model_role))
        )
    )
    if model_role:
        kwargs.setdefault("timeout", get_role_timeout_sec(model_role))
    if use_resp:
        try:
            kwargs = _prepare_chat_completion_kwargs(model, kwargs)
            req: Dict[str, Any] = {"model": model, "input": messages}
            if "max_tokens" in kwargs:
                req["max_output_tokens"] = kwargs.pop("max_tokens")
            if "max_completion_tokens" in kwargs:
                req["max_output_tokens"] = kwargs.pop("max_completion_tokens")
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
    chat_kwargs = _prepare_chat_completion_kwargs(model, kwargs)
    return await async_client.chat.completions.create(model=model, messages=messages, **chat_kwargs)


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
    response = await _invoke_llm_async(
        async_client, model=resolved, messages=messages, model_role=model_role, **kwargs
    )
    api_kind = "responses" if use_responses_api_for_role(model_role) else "completions"
    _record_response(resolved, path, (time.time() - t0) * 1000, response, api_kind=api_kind)
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
