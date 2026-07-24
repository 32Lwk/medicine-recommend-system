"""静的アセット URL 解決（localhost では CDN ではなく /static/ を優先）。"""
from __future__ import annotations

import contextvars
import os

_prefer_local_static: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "prefer_local_static",
    default=False,
)


def is_loopback_host(host: str | None) -> bool:
    h = (host or "").split(":")[0].strip().lower()
    if not h:
        return False
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    return h.startswith("127.")


def set_prefer_local_static(value: bool) -> contextvars.Token[bool]:
    return _prefer_local_static.set(value)


def reset_prefer_local_static(token: contextvars.Token[bool]) -> None:
    _prefer_local_static.reset(token)


def should_prefer_local_static_assets() -> bool:
    """localhost リクエスト時のみ CloudFront ではなく /static/ を使う（middleware が設定）。"""
    if bool(_prefer_local_static.get()):
        return True
    if os.getenv("LOCAL_STATIC_ASSETS", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return False
