"""Unit tests for TypeSafe System One (Jev) HTTP client."""
from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest

from config.routing_config import (
    jev_confidence_floor,
    jev_high_confidence,
    jev_http_max_retries,
    jev_model,
    jev_noul_threshold,
    jev_timeout_sec,
)
from config.llm_flags import (
    is_jev_enabled,
    is_jev_intent_router_primary_enabled,
    is_jev_intent_router_shadow_enabled,
)
from src.services import jev_client as jev_client_mod
from src.services.jev_client import (
    ERROR_HTTP_4XX,
    ERROR_HTTP_429_EXHAUSTED,
    ERROR_HTTP_5XX_EXHAUSTED,
    ERROR_INVALID_JSON,
    ERROR_MISSING_API_KEY,
    ERROR_NETWORK,
    ERROR_TIMEOUT,
    JEV_ENDPOINT,
    build_httpx_timeout,
    evaluate_system_one,
)

SECRET = "super-secret-jev-key-do-not-leak"


@pytest.fixture(autouse=True)
def _clear_jev_env(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEV_MODEL", raising=False)
    monkeypatch.delenv("JEV_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("JEV_CONFIDENCE_FLOOR", raising=False)
    monkeypatch.delenv("JEV_HIGH_CONFIDENCE", raising=False)
    monkeypatch.delenv("JEV_NOUL_THRESHOLD", raising=False)
    jev_client_mod._close_shared_client()
    yield
    jev_client_mod._close_shared_client()


def _mock_client(post_side_effect):
    client = MagicMock()
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
    # Shared client has no constructor timeout; budget is per-request.
    assert "timeout" not in (client_cls.call_args.kwargs or {})
    kwargs = client.post.call_args.kwargs
    timeout_arg = kwargs["timeout"]
    assert isinstance(timeout_arg, httpx.Timeout)
    assert timeout_arg.read == 3.5
    assert timeout_arg.connect == 1.0
    assert kwargs["json"]["state"]["user_input"] == "頭痛"
    assert kwargs["json"]["model"] == "jev-latest"
    assert "questions" in kwargs["json"]
    assert client.post.call_args.args[0] == JEV_ENDPOINT
    assert kwargs["headers"]["Authorization"] == f"Bearer {SECRET}"


def test_empty_meta_omitted_from_wire_payload_reduces_bytes(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])
    state = {"user_input": "頭痛", "recent_turns": [], "recent_context": [], "meta": {}}

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state=state, questions={})

    assert result.ok is True
    sent_state = client.post.call_args.kwargs["json"]["state"]
    assert "meta" not in sent_state
    assert state["meta"] == {}
    raw_payload = {"state": state, "model": "jev-latest", "questions": {}}
    sent_payload = client.post.call_args.kwargs["json"]
    raw_bytes = len(json.dumps(raw_payload, ensure_ascii=False).encode("utf-8"))
    sent_bytes = len(json.dumps(sent_payload, ensure_ascii=False).encode("utf-8"))
    assert sent_bytes < raw_bytes


def test_two_successful_calls_reuse_same_client(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response(), _ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client) as client_cls:
        first = evaluate_system_one(state={"n": 1}, questions={})
        second = evaluate_system_one(state={"n": 2}, questions={})

    assert first.ok is True
    assert second.ok is True
    client_cls.assert_called_once()
    assert client.post.call_count == 2
    assert client.close.call_count == 0


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


def test_network_error_no_retry(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([httpx.ConnectError("boom")])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_NETWORK
    assert result.retry_count == 0
    assert client.post.call_count == 1


def test_invalid_json(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    bad = MagicMock()
    bad.status_code = 200
    bad.json.side_effect = ValueError("not json")
    client = _mock_client([bad])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_INVALID_JSON
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


def test_whitespace_api_key_treated_as_missing(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "   ")
    with patch("src.services.jev_client.httpx.Client") as client_cls:
        result = evaluate_system_one(state={}, questions={})

    assert result.error_class == ERROR_MISSING_API_KEY
    client_cls.assert_not_called()


def test_secret_not_in_result_or_logs(monkeypatch, caplog):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    request = httpx.Request(
        "POST",
        JEV_ENDPOINT,
        headers={"Authorization": f"Bearer {SECRET}", "Content-Type": "application/json"},
    )
    err = httpx.ConnectError("connection failed", request=request)
    client = _mock_client([err])

    with caplog.at_level(logging.WARNING, logger="src.services.jev_client"):
        with patch("src.services.jev_client.httpx.Client", return_value=client):
            result = evaluate_system_one(state={"user_input": "x"}, questions={})

    blob = f"{result!s} {result!r} {result.answers} {result.usage} {result.error_class}"
    assert SECRET not in blob
    assert "Authorization" not in blob
    assert SECRET not in caplog.text
    assert "Authorization" not in caplog.text
    assert "Bearer" not in caplog.text
    assert result.ok is False
    assert result.error_class == ERROR_NETWORK


def test_secret_not_leaked_on_success_repr(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert SECRET not in str(result)
    assert SECRET not in repr(result)


def test_build_httpx_timeout_splits_connect_and_read():
    t = build_httpx_timeout(3.5)
    assert t.connect == 1.0
    assert t.read == 3.5
    t_short = build_httpx_timeout(0.5)
    assert t_short.connect == 0.5
    assert t_short.read == 0.5


def test_custom_timeout_passed_to_post(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client) as client_cls:
        evaluate_system_one(state={}, questions={}, timeout_sec=2.0)

    assert "timeout" not in (client_cls.call_args.kwargs or {})
    timeout_arg = client.post.call_args.kwargs["timeout"]
    assert timeout_arg.read == 2.0
    assert timeout_arg.connect == 1.0


def test_resolved_version_absent_is_none(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client(
        [
            _ok_response(
                payload={
                    "answers": {},
                    "usage": {},
                    "model": "jev-latest",
                }
            )
        ]
    )

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is True
    assert result.resolved_version is None


# --- Fault injection (transport) ---


def test_dns_failure_no_retry(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    err = httpx.ConnectError("[Errno 11001] getaddrinfo failed")
    client = _mock_client([err])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_NETWORK
    assert result.retry_count == 0
    assert client.post.call_count == 1


def test_connection_refused_no_retry(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    err = httpx.ConnectError("[WinError 10061] Connection refused")
    client = _mock_client([err])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_NETWORK
    assert result.retry_count == 0
    assert client.post.call_count == 1


def test_500_exhausted(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    r1 = MagicMock()
    r1.status_code = 500
    r2 = MagicMock()
    r2.status_code = 500
    client = _mock_client([r1, r2])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_HTTP_5XX_EXHAUSTED
    assert result.retry_count == 1
    assert result.status_code == 500
    assert client.post.call_count == 2


def test_503_then_success(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    first = MagicMock()
    first.status_code = 503
    client = _mock_client([first, _ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is True
    assert result.retry_count == 1
    assert client.post.call_count == 2


def test_malformed_json_non_object(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    bad = MagicMock()
    bad.status_code = 200
    bad.json.return_value = ["not", "a", "dict"]
    client = _mock_client([bad])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == ERROR_INVALID_JSON
    assert result.retry_count == 0


def test_usage_missing_returns_empty_dict(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client(
        [
            _ok_response(
                payload={
                    "answers": {"primary_route": {"type": "choice", "choice": "Physical"}},
                    "model": "jev-latest",
                }
            )
        ]
    )

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is True
    assert result.usage == {}
    assert result.answers["primary_route"]["choice"] == "Physical"


def test_answers_missing_returns_empty_dict(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client(
        [
            _ok_response(
                payload={
                    "usage": {"input_tokens": 1},
                    "model": "jev-latest",
                }
            )
        ]
    )

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is True
    assert result.answers == {}
    assert result.usage == {"input_tokens": 1}


def test_close_shared_client_idempotent(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", SECRET)
    client = _mock_client([_ok_response()])

    with patch("src.services.jev_client.httpx.Client", return_value=client):
        evaluate_system_one(state={}, questions={})
        assert jev_client_mod._shared_client is client
        jev_client_mod._close_shared_client()
        assert jev_client_mod._shared_client is None
        jev_client_mod._close_shared_client()  # second close must not raise
        assert jev_client_mod._shared_client is None
    assert client.close.call_count >= 1


def test_client_constructor_failure_fail_open(monkeypatch):
    """Shared client construction must not raise to callers."""
    monkeypatch.setenv("JEV_API_KEY", SECRET)

    with patch(
        "src.services.jev_client.httpx.Client",
        side_effect=RuntimeError("pool init failed"),
    ):
        result = evaluate_system_one(state={}, questions={})

    assert result.ok is False
    assert result.error_class == "unexpected"


# --- routing_config Jev getters ---


def test_routing_config_jev_defaults():
    assert jev_model() == "jev-latest"
    assert jev_timeout_sec() == 3.5
    assert jev_http_max_retries() == 1
    assert jev_confidence_floor() == 0.70
    assert jev_high_confidence() == 0.85
    assert jev_noul_threshold() == 0.75


def test_routing_config_timeout_clamp_and_invalid(monkeypatch):
    monkeypatch.setenv("JEV_TIMEOUT_SEC", "99")
    assert jev_timeout_sec() == 30.0
    monkeypatch.setenv("JEV_TIMEOUT_SEC", "0.1")
    assert jev_timeout_sec() == 0.5
    monkeypatch.setenv("JEV_TIMEOUT_SEC", "not-a-float")
    assert jev_timeout_sec() == 3.5


def test_routing_config_model_empty_falls_back(monkeypatch):
    monkeypatch.setenv("JEV_MODEL", "  ")
    assert jev_model() == "jev-latest"
    monkeypatch.setenv("JEV_MODEL", "jev-canary")
    assert jev_model() == "jev-canary"


@pytest.mark.parametrize(
    "env_name,getter,default",
    [
        ("JEV_CONFIDENCE_FLOOR", jev_confidence_floor, 0.70),
        ("JEV_HIGH_CONFIDENCE", jev_high_confidence, 0.85),
        ("JEV_NOUL_THRESHOLD", jev_noul_threshold, 0.75),
    ],
)
def test_routing_config_unit_interval_out_of_range_uses_default(monkeypatch, env_name, getter, default):
    monkeypatch.setenv(env_name, "-0.1")
    assert getter() == default
    monkeypatch.setenv(env_name, "1.01")
    assert getter() == default
    monkeypatch.setenv(env_name, "nan")
    assert getter() == default
    monkeypatch.setenv(env_name, "nope")
    assert getter() == default


@pytest.mark.parametrize(
    "env_name,getter",
    [
        ("JEV_CONFIDENCE_FLOOR", jev_confidence_floor),
        ("JEV_HIGH_CONFIDENCE", jev_high_confidence),
        ("JEV_NOUL_THRESHOLD", jev_noul_threshold),
    ],
)
def test_routing_config_unit_interval_accepts_bounds(monkeypatch, env_name, getter):
    monkeypatch.setenv(env_name, "0.0")
    assert getter() == 0.0
    monkeypatch.setenv(env_name, "1.0")
    assert getter() == 1.0
    monkeypatch.setenv(env_name, "0.42")
    assert getter() == 0.42


# --- llm_flags: default OFF + PRIMARY must stay inert for Phase1 adapters ---


def test_jev_flags_default_off(monkeypatch):
    for name in ("JEV_ENABLED", "JEV_INTENT_ROUTER_SHADOW", "JEV_INTENT_ROUTER_PRIMARY"):
        monkeypatch.delenv(name, raising=False)
    assert is_jev_enabled() is False
    assert is_jev_intent_router_shadow_enabled() is False
    assert is_jev_intent_router_primary_enabled() is False


def test_jev_primary_flag_not_referenced_by_client_module():
    """Phase1: client must not branch on PRIMARY (execution remains fail-open transport)."""
    import inspect

    from src.services import jev_client

    source = inspect.getsource(jev_client)
    assert "JEV_INTENT_ROUTER_PRIMARY" not in source
    assert "is_jev_intent_router_primary" not in source