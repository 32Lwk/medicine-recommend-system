"""TypeSafe System One (Jev) HTTP client — transport only.

Route mapping / IntentRouter 判断は行わない。auth・timeout・retry・usage 返却のみ。

Callers (shadow / metrics):
- Persist ``JevClientResult.resolved_version`` (and ``model`` / ``usage`` /
  ``latency_ms`` / ``retry_count`` / ``error_class``) into metrics / JSONL when
  present. The client does not emit metrics itself.
- Never log ``Authorization``, API keys, or raw response bodies. Do not use
  ``logger.exception`` / ``exc_info=True`` around this client — httpx request
  objects can embed the Bearer token in exception chains.
"""
from __future__ import annotations

import atexit
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config.routing_config import jev_http_max_retries as configured_jev_http_max_retries
from config.routing_config import jev_model as configured_jev_model
from config.routing_config import jev_retry_jitter_ms as configured_jev_retry_jitter_ms
from config.routing_config import jev_timeout_sec as configured_jev_timeout_sec

logger = logging.getLogger(__name__)

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"

ERROR_MISSING_API_KEY = "missing_api_key"
ERROR_TIMEOUT = "timeout"
ERROR_HTTP_4XX = "http_4xx"
ERROR_HTTP_429_EXHAUSTED = "http_429_exhausted"
ERROR_HTTP_5XX_EXHAUSTED = "http_5xx_exhausted"
ERROR_NETWORK = "network_error"
ERROR_INVALID_JSON = "invalid_json"
ERROR_UNEXPECTED = "unexpected"

_CONNECT_TIMEOUT_CAP_SEC = 1.0


def _max_attempts() -> int:
    """initial + configured retries (default 1 + 1 = 2; env 0..2 extras)."""
    retries = int(configured_jev_http_max_retries())
    if retries < 0:
        retries = 0
    return 1 + retries


def _retry_jitter_sleep() -> None:
    """Sleep a small random jitter before a 429/5xx retry (no PII)."""
    try:
        import random

        lo_ms, hi_ms = configured_jev_retry_jitter_ms()
        delay = random.uniform(lo_ms / 1000.0, hi_ms / 1000.0)
        if delay > 0:
            time.sleep(delay)
    except Exception:
        pass

_client_lock = threading.Lock()
_shared_client: httpx.Client | None = None


@dataclass(frozen=True)
class JevClientResult:
    """Transport result for a System One evaluate call.

    ``resolved_version`` is opaque vendor metadata when present; metrics /
    shadow adapters should forward it as-is (string or null). Never put secrets
    into this dataclass.
    """

    ok: bool
    answers: dict[str, Any] | None
    usage: dict[str, Any] | None
    latency_ms: float
    retry_count: int
    error_class: str | None
    status_code: int | None
    model: str | None
    resolved_version: str | None = None


def _latency_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _normalize_timeout_sec(timeout_sec: float | None) -> float:
    if timeout_sec is None:
        timeout = float(configured_jev_timeout_sec())
    else:
        try:
            timeout = float(timeout_sec)
        except (TypeError, ValueError):
            timeout = 3.5
    if timeout != timeout:  # NaN
        timeout = 3.5
    return max(0.5, min(30.0, timeout))


def build_httpx_timeout(timeout_sec: float) -> httpx.Timeout:
    """Split connect vs read so dead endpoints fail fast within the budget.

    - ``read`` / default: full ``timeout_sec`` (System One inference budget)
    - ``connect``: min(1.0, timeout_sec) — do not burn the whole budget on TCP
    """
    total = _normalize_timeout_sec(timeout_sec)
    connect = min(_CONNECT_TIMEOUT_CAP_SEC, total)
    return httpx.Timeout(total, connect=connect)


def _close_shared_client() -> None:
    """Close the process-level httpx client (atexit / tests)."""
    global _shared_client
    with _client_lock:
        client = _shared_client
        _shared_client = None
    if client is None:
        return
    try:
        client.close()
    except Exception:
        # Never raise from cleanup; never log (close errors may embed request state).
        pass


def _get_shared_client() -> httpx.Client:
    """Return a process-level httpx.Client (thread-safe lazy init).

    Timeout is applied per-request in ``evaluate_system_one``, not on the
    shared Client constructor, so callers can vary budgets without recreating
    the connection pool.
    """
    global _shared_client
    client = _shared_client
    if client is not None:
        return client
    with _client_lock:
        if _shared_client is None:
            # No default timeout — each post() passes its own Timeout.
            _shared_client = httpx.Client()
        return _shared_client


atexit.register(_close_shared_client)


def _fail(
    *,
    started: float,
    error_class: str,
    retry_count: int,
    model: str | None,
    status_code: int | None = None,
) -> JevClientResult:
    return JevClientResult(
        ok=False,
        answers=None,
        usage=None,
        latency_ms=_latency_ms(started),
        retry_count=retry_count,
        error_class=error_class,
        status_code=status_code,
        model=model,
        resolved_version=None,
    )


def _safe_log(msg: str, *args: Any) -> None:
    """Warning without exc_info — never attach exception chains (may hold Bearer)."""
    logger.warning(msg, *args)


def _compact_outbound_state(state: dict[str, Any]) -> dict[str, Any]:
    """Drop wire-only empty optionals without mutating the caller-owned state."""
    compact = dict(state)
    meta = compact.get("meta")
    if isinstance(meta, dict) and not meta:
        compact.pop("meta", None)
    return compact


def evaluate_system_one(
    *,
    state: dict[str, Any],
    questions: dict[str, Any],
    model: str | None = None,
    timeout_sec: float | None = None,
) -> JevClientResult:
    """POST state/questions to TypeSafe System One.

    Auth: ``JEV_API_KEY`` only (no ``TYPESAFE_API_KEY`` fallback).
    Retry: once on HTTP 429 / 5xx only. Timeout / other 4xx / network: no retry.
    Never raises for expected transport failures; returns structured ``JevClientResult``.

    On success, ``resolved_version`` is copied from the JSON body when present so
    callers can attach it to metrics / shadow events without re-parsing the body.
    """
    started = time.perf_counter()
    resolved_model = (model or configured_jev_model() or "jev-latest").strip() or "jev-latest"
    timeout = _normalize_timeout_sec(timeout_sec)
    http_timeout = build_httpx_timeout(timeout)

    api_key = os.getenv("JEV_API_KEY")
    if not (api_key and str(api_key).strip()):
        return _fail(
            started=started,
            error_class=ERROR_MISSING_API_KEY,
            retry_count=0,
            model=resolved_model,
        )

    # Build auth header locally; never put the key into logs or result fields.
    headers = {
        "Authorization": f"Bearer {str(api_key).strip()}",
        "Content-Type": "application/json",
    }
    # Drop the env string reference ASAP (header still holds the token for the request).
    api_key = None

    payload = {
        "state": _compact_outbound_state(state),
        "model": resolved_model,
        "questions": questions,
    }

    retry_count = 0
    last_status: int | None = None
    max_attempts = _max_attempts()

    try:
        client = _get_shared_client()
        for attempt in range(max_attempts):
            try:
                response = client.post(
                    JEV_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=http_timeout,
                )
            except httpx.TimeoutException:
                # Do not retry timeouts. Do not log exception text / exc_info.
                _safe_log(
                    "jev_client timeout error_class=%s attempt=%s",
                    ERROR_TIMEOUT,
                    attempt,
                )
                return _fail(
                    started=started,
                    error_class=ERROR_TIMEOUT,
                    retry_count=retry_count,
                    model=resolved_model,
                )
            except httpx.RequestError:
                # DNS / connection refused / other network: no retry.
                # Exception may embed request headers (Authorization) —
                # never log or re-raise the object.
                _safe_log(
                    "jev_client network_error error_class=%s attempt=%s",
                    ERROR_NETWORK,
                    attempt,
                )
                return _fail(
                    started=started,
                    error_class=ERROR_NETWORK,
                    retry_count=retry_count,
                    model=resolved_model,
                )

            status = int(response.status_code)
            last_status = status

            if status == 429 or status >= 500:
                if attempt + 1 < max_attempts:
                    retry_count += 1
                    _safe_log(
                        "jev_client retryable status=%s retry_count=%s",
                        status,
                        retry_count,
                    )
                    _retry_jitter_sleep()
                    continue
                error_class = (
                    ERROR_HTTP_429_EXHAUSTED if status == 429 else ERROR_HTTP_5XX_EXHAUSTED
                )
                _safe_log(
                    "jev_client exhausted error_class=%s status=%s",
                    error_class,
                    status,
                )
                return _fail(
                    started=started,
                    error_class=error_class,
                    retry_count=retry_count,
                    model=resolved_model,
                    status_code=status,
                )

            if 400 <= status < 500:
                # Non-429 4xx: no retry. Never log response body.
                _safe_log(
                    "jev_client http_4xx status=%s retry_count=%s",
                    status,
                    retry_count,
                )
                return _fail(
                    started=started,
                    error_class=ERROR_HTTP_4XX,
                    retry_count=retry_count,
                    model=resolved_model,
                    status_code=status,
                )

            if status < 200 or status >= 300:
                _safe_log("jev_client unexpected status=%s", status)
                return _fail(
                    started=started,
                    error_class=ERROR_UNEXPECTED,
                    retry_count=retry_count,
                    model=resolved_model,
                    status_code=status,
                )

            try:
                raw = response.json()
            except Exception:
                _safe_log("jev_client invalid_json status=%s", status)
                return _fail(
                    started=started,
                    error_class=ERROR_INVALID_JSON,
                    retry_count=retry_count,
                    model=resolved_model,
                    status_code=status,
                )

            if not isinstance(raw, dict):
                return _fail(
                    started=started,
                    error_class=ERROR_INVALID_JSON,
                    retry_count=retry_count,
                    model=resolved_model,
                    status_code=status,
                )

            answers = raw.get("answers")
            usage = raw.get("usage")
            response_model = raw.get("model")
            resolved_version = raw.get("resolved_version")

            return JevClientResult(
                ok=True,
                answers=answers if isinstance(answers, dict) else {},
                usage=usage if isinstance(usage, dict) else {},
                latency_ms=_latency_ms(started),
                retry_count=retry_count,
                error_class=None,
                status_code=status,
                model=str(response_model) if response_model is not None else resolved_model,
                resolved_version=(
                    str(resolved_version) if resolved_version is not None else None
                ),
            )
    except Exception:
        # Catch-all: never crash callers; never log exception text / exc_info.
        _safe_log(
            "jev_client unexpected error_class=%s last_status=%s",
            ERROR_UNEXPECTED,
            last_status,
        )
        return _fail(
            started=started,
            error_class=ERROR_UNEXPECTED,
            retry_count=retry_count,
            model=resolved_model,
            status_code=last_status,
        )

    return _fail(
        started=started,
        error_class=ERROR_UNEXPECTED,
        retry_count=retry_count,
        model=resolved_model,
        status_code=last_status,
    )
