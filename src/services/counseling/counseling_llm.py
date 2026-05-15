"""カウンセリング系モジュール共通の LLM 呼び出し（同期・並列）"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from src.core.i18n_prompts import append_language_instruction, normalize_lang
from src.core.llm_client import (
    chat_completion_create,
    chat_completion_create_async,
    gather_llm_tasks,
    get_async_client,
    run_async,
)


def _with_lang(messages: List[Dict[str, str]], lang: str) -> List[Dict[str, str]]:
    if not messages or lang == "ja":
        return messages
    out = list(messages)
    last = out[-1]
    if last.get("role") == "user":
        out[-1] = {
            **last,
            "content": append_language_instruction(last.get("content", ""), lang),
        }
    return out


def counseling_chat(
    client: OpenAI,
    path: str,
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 800,
    temperature: float = 0.7,
    response_format: Optional[Dict] = None,
    lang: str = "ja",
) -> Any:
    kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format
    return chat_completion_create(
        client,
        model_role="counsel",
        path=path,
        messages=_with_lang(messages, lang),
        **kwargs,
    )


def counseling_chat_parallel(
    client: OpenAI,
    calls: List[Tuple[str, List[Dict[str, str]], Dict[str, Any]]],
    *,
    lang: str = "ja",
) -> List[Any]:
    """
    複数のカウンセリング LLM 呼び出しを並列実行。
    calls: [(path, messages, kwargs), ...]
    """
    if len(calls) <= 1:
        if not calls:
            return []
        path, messages, kw = calls[0]
        return [counseling_chat(client, path, messages, lang=lang, **kw)]

    async def _run_all():
        async_client = get_async_client()
        coros = []
        for path, messages, kw in calls:
            merged = dict(kw)
            merged.setdefault("max_tokens", 800)
            merged.setdefault("temperature", 0.7)
            rf = merged.pop("response_format", None)
            msgs = _with_lang(messages, lang)
            coros.append(
                chat_completion_create_async(
                    async_client,
                    model_role="counsel",
                    path=path,
                    messages=msgs,
                    response_format=rf,
                    **merged,
                )
            )
        return await gather_llm_tasks(*coros)

    results = run_async(_run_all())
    out: List[Any] = []
    for r in results:
        if isinstance(r, Exception):
            raise r
        out.append(r)
    return out
