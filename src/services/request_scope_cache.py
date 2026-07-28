"""リクエスト（1 POST）スコープの LLM 結果メモ化。"""
from __future__ import annotations

import contextvars
from typing import Any, Callable, Hashable, Optional, TypeVar

T = TypeVar("T")

_cache_var: contextvars.ContextVar[Optional[dict[Hashable, Any]]] = contextvars.ContextVar(
    "request_scope_llm_cache",
    default=None,
)


def _store() -> dict[Hashable, Any]:
    store = _cache_var.get()
    if store is None:
        store = {}
        _cache_var.set(store)
    return store


def get_or_set(key: Hashable, factory: Callable[[], T]) -> T:
    store = _store()
    if key in store:
        return store[key]  # type: ignore[return-value]
    value = factory()
    store[key] = value
    return value


def clear_request_scope_cache() -> None:
    _cache_var.set({})
