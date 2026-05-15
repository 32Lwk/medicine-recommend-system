"""リクエストスコープの LLM プロファイル上書き（カナリア用）"""
from __future__ import annotations

import contextvars
from typing import Optional

_profile_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "llm_profile_override", default=None
)


def set_request_profile(profile: Optional[str]) -> None:
    _profile_var.set(profile)


def get_request_profile() -> Optional[str]:
    return _profile_var.get()


def clear_request_profile() -> None:
    _profile_var.set(None)
