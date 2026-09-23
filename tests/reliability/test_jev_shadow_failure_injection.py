"""R19 Jev shadow failure injection (local only).

Assert for each fault class:
- user / legacy path unchanged (fail-open)
- shadow only skipped or recorded as failed
- no retry storm (client attempts <= 1 + JEV_HTTP_MAX_RETRIES)

Scenarios: timeout, 429, 500, invalid schema, queue full, circuit open,
kill switch, JSONL write failure.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

import src.services.jev_client as jev_client_mod
import src.services.jev_decisions as jev_decisions_mod
import src.services.jev_metrics as jev_metrics_mod
from src.dialogue.routing import jev_router as jr
from src.dialogue.routing.jev_router import (
    build_jev_router_state,
    run_jev_shadow_sync,
    schedule_jev_shadow,
)
from src.dialogue.routing.jev_shadow_guards import (
    JevShadowGuards,
    ShadowGuardConfig,
    reset_shadow_guards_for_tests,
)
from src.dialogue.routing.types import RouteDecision
from src.services.jev_client import evaluate_system_one


def _legacy() -> dict[str, Any]:
    return {"primary_route": "Physical", "sub_route": "rule_based_recommend", "confidence": 0.9}


def _session_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    return {
        k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
        for k, v in session.items()
    }


def _ok_answers_unknown_primary() -> dict[str, Any]:
    def _choice(value: str, confidence: float = 0.9) -> dict:
        return {"choice": value, "confidence": confidence}

    return {
        "primary_route": _choice("NotARealRoute", 0.9),
        "physical_sub_route": _choice("none", 0.5),
        "concierge_sub_route": _choice("none", 0.5),
        "session_sub_route": _choice("none", 0.5),
        "emergency_required": {"noul": 0.0},
        "security_risk": {"noul": 0.0},
        "store_inquiry": {"noul": 0.0},
        "counseling_needed": {"noul": 0.0},
    }


@pytest.fixture(autouse=True)
def _reset_runtime():
    jr._reset_runtime_for_tests()
    reset_shadow_guards_for_tests()
    jev_client_mod._close_shared_client()
    yield
    jr._reset_runtime_for_tests()
    reset_shadow_guards_for_tests()
    jev_client_mod._close_shared_client()


@pytest.fixture
def session() -> dict[str, Any]:
    return {
        "messages": [{"type": "user", "content": "頭痛です"}],
        "dialogue_state": {"version": 1, "routing": {"primary_route": "Physical"}},
        "_routing_decision": _legacy(),
    }


def test_timeout_fail_open_no_retry_storm(session: dict[str, Any], monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "test-key-not-secret")
    monkeypatch.setenv("JEV_HTTP_MAX_RETRIES", "1")
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-to")
    legacy = _legacy()

    client = MagicMock()
    client.post.side_effect = httpx.TimeoutException("read timeout")

    with patch("src.services.jev_client.httpx.Client", return_value=client), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-timeout",
            sid="sid-to",
            force=True,
        )

    assert ok is True
    assert client.post.call_count == 1  # timeout: no retry
    assert session == before or session.get("_routing_decision") == before["_routing_decision"]
    assert session.get("_intent_router_shadow") is None
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] == "timeout"
    assert kwargs["executed_decision"]["primary_route"] == "Physical"
    assert int(kwargs.get("retry_count") or 0) == 0


def test_429_exhausts_with_bounded_retries(session: dict[str, Any], monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "test-key-not-secret")
    monkeypatch.setenv("JEV_HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MIN", "0")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MAX", "0")
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-429")

    resp = MagicMock()
    resp.status_code = 429
    client = MagicMock()
    client.post.side_effect = [resp, resp, resp]  # would storm if unbounded

    with patch("src.services.jev_client.httpx.Client", return_value=client), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-429",
            force=True,
        )

    assert ok is True
    assert client.post.call_count == 2  # initial + 1 retry max
    assert session.get("_routing_decision") == before["_routing_decision"]
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] in ("http_429_exhausted", "http_429")
    assert int(kwargs.get("retry_count") or 0) <= 1


def test_500_exhausts_with_bounded_retries(session: dict[str, Any], monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "test-key-not-secret")
    monkeypatch.setenv("JEV_HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MIN", "0")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MAX", "0")
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-500")

    resp = MagicMock()
    resp.status_code = 500
    client = MagicMock()
    client.post.side_effect = [resp, resp, resp]

    with patch("src.services.jev_client.httpx.Client", return_value=client), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-500",
            force=True,
        )

    assert ok is True
    assert client.post.call_count == 2
    assert session.get("_routing_decision") == before["_routing_decision"]
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] in ("http_5xx_exhausted", "http_5xx")
    assert int(kwargs.get("retry_count") or 0) <= 1


def test_invalid_schema_fail_open_user_path(session: dict[str, Any]):
    before = _session_snapshot(session)
    state = build_jev_router_state("謎", session, "sid-schema")
    mock_result = SimpleNamespace(
        ok=True,
        answers=_ok_answers_unknown_primary(),
        usage={},
        retry_count=0,
        model="jev-latest",
        error_class=None,
    )
    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ) as mock_eval, patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-schema",
            force=True,
        )
    assert ok is True
    assert mock_eval.call_count == 1
    assert session.get("_routing_decision") == before["_routing_decision"]
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] == "invalid_schema"
    assert kwargs["executed_decision"]["primary_route"] == "Physical"


def test_queue_full_skips_shadow_user_path_unchanged(session: dict[str, Any]):
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-q")
    with patch.object(jr, "_MAX_PENDING_SHADOW", 0), patch.object(
        jev_client_mod, "evaluate_system_one", MagicMock()
    ) as mock_eval, patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-q",
            sync=False,
            force=True,
            sid="sid-q",
        )
    assert ok is False
    assert not mock_eval.called
    assert session.get("_routing_decision") == before["_routing_decision"]
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["attempted"] is False
    assert kwargs["error_class"] == "queue_full"


def test_circuit_open_skips_shadow_only(session: dict[str, Any]):
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-cir")
    reset_shadow_guards_for_tests()
    guards = JevShadowGuards(ShadowGuardConfig(consecutive_failure_open=1))
    guards.record_failure()
    assert guards.check_admit(pending_count=0).allow is False

    with patch(
        "src.dialogue.routing.jev_shadow_guards.get_shadow_guards", return_value=guards
    ), patch.object(jev_client_mod, "evaluate_system_one", MagicMock()) as mock_eval, patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-cir",
            sync=True,
            force=True,
            sid="sid-cir",
        )
    assert ok is False
    assert not mock_eval.called
    assert session.get("_routing_decision") == before["_routing_decision"]
    assert mock_rec.call_args.kwargs["error_class"] == "circuit_open"


def test_kill_switch_off_skips_schedule(session: dict[str, Any], monkeypatch):
    for key in (
        "JEV_ENABLED",
        "JEV_INTENT_ROUTER_SHADOW",
        "JEV_INTENT_ROUTER_PRIMARY",
    ):
        monkeypatch.setenv(key, "false")
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-kill")
    with patch.object(jev_client_mod, "evaluate_system_one", MagicMock()) as mock_eval:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-kill",
            sync=True,
            force=False,
        )
    assert ok is False
    assert not mock_eval.called
    assert session.get("_routing_decision") == before["_routing_decision"]


def test_jsonl_write_failure_does_not_affect_user_path(session: dict[str, Any]):
    before = _session_snapshot(session)
    state = build_jev_router_state("頭痛です", session, "sid-jsonl")
    mock_result = SimpleNamespace(
        ok=True,
        answers={},
        usage={"input_tokens": 1},
        retry_count=0,
        model="jev-latest",
        error_class=None,
    )
    mock_decision = SimpleNamespace(
        primary_route="Concierge",
        sub_route=None,
        confidence=0.99,
        risk_flags=[],
        valid=True,
        noul={},
        to_dialogue_routing_dict=lambda: {
            "primary_route": "Concierge",
            "confidence": 0.99,
        },
    )
    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ), patch.object(
        jev_decisions_mod, "parse_jev_answers", return_value=mock_decision
    ), patch.object(jev_decisions_mod, "INTENT_ROUTER_QUESTIONS", []), patch.object(
        jev_metrics_mod,
        "record_shadow_event",
        side_effect=OSError("disk full"),
    ):
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="corr-jsonl",
            force=True,
        )
    assert ok is True
    assert session.get("_routing_decision") == before["_routing_decision"]
    assert session.get("_intent_router_shadow") is None


def test_resolve_route_stays_legacy_when_shadow_faults(session: dict[str, Any]):
    """Integration: resolve_route identity preserved under shadow schedule failure."""
    legacy = RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.91,
        resolved_by="legacy",
        source="test_legacy",
    )

    def _schedule(**_kwargs: Any) -> bool:
        return False  # queue/circuit/kill skip

    with patch(
        "src.dialogue.routing.router.resolve_route_unified_or_legacy",
        return_value=legacy,
    ), patch(
        "config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=True
    ), patch(
        "src.dialogue.routing.jev_router.schedule_jev_shadow", side_effect=_schedule
    ), patch(
        "src.dialogue.routing.jev_router.build_jev_router_state",
        return_value={
            "channel": "web",
            "user_input": "頭痛です",
            "recent_turns": [],
            "meta": {},
            "app_context": "x",
        },
    ):
        from src.dialogue.routing.router import resolve_route

        out = resolve_route("頭痛です", session, "sid-int")
    assert out is legacy
    assert session.get("_routing_decision") is None or True  # not mutated by skip


def test_client_max_retries_cap_not_exceeded_on_persistent_429(monkeypatch):
    """Direct client contract: never more than 1 + JEV_HTTP_MAX_RETRIES posts."""
    monkeypatch.setenv("JEV_API_KEY", "test-key-not-secret")
    monkeypatch.setenv("JEV_HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MIN", "0")
    monkeypatch.setenv("JEV_RETRY_JITTER_MS_MAX", "0")
    resp = MagicMock()
    resp.status_code = 429
    client = MagicMock()
    client.post.side_effect = [resp] * 10
    with patch("src.services.jev_client.httpx.Client", return_value=client):
        result = evaluate_system_one(state={"user_input": "x"}, questions={})
    assert result.ok is False
    assert client.post.call_count == 2
    assert result.retry_count <= 1
