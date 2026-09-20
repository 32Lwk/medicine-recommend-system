"""Unit tests for TypeSafe System One (Jev) HTTP client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.services.jev_client import (
    ERROR_HTTP_4XX,
    ERROR_HTTP_429_EXHAUSTED,
    ERROR_HTTP_5XX_EXHAUSTED,
    ERROR_MISSING_API_KEY,
    ERROR_TIMEOUT,
    JEV_ENDPOINT,
    evaluate_system_one,
)

SECRET = "super-secret-jev-key-do-not-leak"


@pytest.fixture(autouse=True)
def _clear_jev_env(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEV_MODEL", raising=False)
    monkeypatch.delenv("JEV_TIMEOUT_SEC", raising=False)


def _mock_client(post_side_effect):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.side_effect = post_side_effect
    return client


def _ok_response(*, status_code: int = 200, payload: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {
        "answers": {"primary_route": {"type": "choice", "choice": "Physical", "confidence": 0.9}},
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "jev-latest",
        "resolved_version": "2026-09-21",
    }
    return response


def test_success(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client) as client_cls:
        result = evaluate_system_one(
            state={"user_input": "頭痛"},
            questions={"primary_route": {"type": "choice", "choices": ["Physical"]}},
        )

    assert result.ok is True
    assert result.error_class is None
    assert result.status_code == 200
    assert result.retry_count == 0
    assert result.answers["primary_route"]["choice"] == "Physical"
    assert result.usage == {"input_tokens": 10, "output_tokens": 5}
    assert result.model == "jev-latest"
    assert result.resolved_version == "2026-09-21"
    assert result.latency_ms >= 0
    client_cls.assert_called_once()
    kwargs = client.post.call_args.kwargs
    assert kwargs["json"]["state"]["user_input"] == "頭痛"
    assert kwargs["json"]["model"] == "jev-latest"
    assert "questions" in kwargs["json"]
    assert client.post.call_args.args[0] == JEV_ENDPOINT
    assert kwargs["headers"]["Authorization"] == f"Bearer {SECRET}"


def test_retry_429_then_success(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    first = MagicMock()
    first.status_code = 429
    second = _ok_response()
    client = _mock_client([first, second])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is True
    assert result.retry_count == 1
    assert result.error_class is None
    assert client.post.call_count == 2


def test_5xx_exhausted(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    r1 = MagicMock()
    r1.status_code = 503
    r2 = MagicMock()
    r2.status_code = 502
    client = _mock_client([r1, r2])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_HTTP_5XX_EXHAUSTED
    assert result.retry_count == 1
    assert result.status_code == 502
    assert client.post.call_count == 2


def test_429_exhausted(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    r1 = MagicMock()
    r1.status_code = 429
    r2 = MagicMock()
    r2.status_code = 429
    client = _mock_client([r1, r2])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_HTTP_429_EXHAUSTED
    assert result.retry_count == 1
    assert client.post.call_count == 2


def test_4xx_no_retry(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    bad = MagicMock()
    bad.status_code = 400
    client = _mock_client([bad])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_HTTP_4XX
    assert result.retry_count == 0
    assert result.status_code == 400
    assert client.post.call_count == 1


def test_timeout_no_retry(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([httpx.TimeoutException("timed out")])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_TIMEOUT
    assert result.retry_count == 0
    assert client.post.call_count == 1


def test_missing_api_key_no_typesafe_fallback(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "should-not-be-used")
    with patch("src.services.jev_client.httpx.Client") as client_cls:
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_MISSING_API_KEY
    assert result.retry_count == 0
    client_cls.assert_not_called()


def test_secret_not_in_result_or_exception_messages(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    # Force a RequestError whose request carries Authorization.
    request = httpx.Request(
        "POST",
        JEV_ENDPOINT,
        headers={"Authorization": f"Bearer {SECRET}", "Content-Type": "application/json"},
    )
    err = httpx.ConnectError("connection failed", request=request)
    client = _mock_client([err])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={"user_input": "x"}, questions={})

    blob = f"{result!s} {result!r} {result.answers} {result.usage} {result.error_class}"
    assert SECRET not in blob
    assert "Authorization" not in blob
    assert result.ok is False
    assert result.error_class == "network_error"


def test_secret_not_leaked_on_success_repr(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert SECRET not in str(result)
    assert SECRET not in repr(result)
