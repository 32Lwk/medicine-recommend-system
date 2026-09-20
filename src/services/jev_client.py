"""TypeSafe System One (Jev) HTTP client — transport only.

Route mapping / IntentRouter 判断は行わない。auth・timeout・retry・usage 返却のみ。
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config.routing_config import jev_model as configured_jev_model
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

_MAX_ATTEMPTS = 2  # initial + 1 retry (429 / 5xx only)


@dataclass(frozen=True)
class JevClientResult:
    """Transport result for a System One evaluate call."""

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
    """
    started = time.perf_counter()
    resolved_model = (model or configured_jev_model() or "jev-latest").strip() or "jev-latest"
    timeout = float(timeout_sec) if timeout_sec is not None else float(configured_jev_timeout_sec())
    if timeout != timeout:  # NaN
        timeout = 3.5
    timeout = max(0.5, min(30.0, timeout))

    api_key = os.getenv("JEV_API_KEY")
    if not (api_key and str(api_key).strip()):
        return _fail(
            started=started,
            error_class=ERROR_MISSING_API_KEY,
            retry_count=0,
            model=resolved_model,
        )

    payload = {
        "state": state,
        "model": resolved_model,
        "questions": questions,
    }
    headers = {
        "Authorization": f"Bearer {str(api_key).strip()}",
        "Content-Type": "application/json",
    }

    retry_count = 0
    last_status: int | None = None

    try:
        with httpx.Client(timeout=timeout) as client:
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    response = client.post(JEV_ENDPOINT, headers=headers, json=payload)
                except httpx.TimeoutException:
                    # Do not retry timeouts.
                    logger.warning(
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
                    # Connection / network errors: no retry. Do not log exception text
                    # (may embed request headers including Authorization).
                    logger.warning(
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
                    if attempt + 1 < _MAX_ATTEMPTS:
                        retry_count += 1
                        logger.warning(
                            "jev_client retryable status=%s retry_count=%s",
                            status,
                            retry_count,
                        )
                        continue
                    error_class = (
                        ERROR_HTTP_429_EXHAUSTED if status == 429 else ERROR_HTTP_5XX_EXHAUSTED
                    )
                    logger.warning(
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
                    logger.warning(
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
                    logger.warning(
                        "jev_client unexpected status=%s",
                        status,
                    )
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
                    logger.warning(
                        "jev_client invalid_json status=%s",
                        status,
                    )
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
        # Catch-all: never crash callers; never log exception text (may contain secrets).
        logger.warning(
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
