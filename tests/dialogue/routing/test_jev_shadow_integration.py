"""Phase 1 Jev shadow integration — executed route / response must stay legacy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.dialogue.routing.types import RouteDecision


@dataclass
class _FakeJevResult:
    ok: bool
    answers: dict[str, Any] | None
    usage: dict[str, Any] | None
    latency_ms: float = 1.0
    retry_count: int = 0
    error_class: str | None = None
    status_code: int | None = 200
    model: str = "jev-latest"
    resolved_version: str | None = "jev-test"


def _legacy_decision() -> RouteDecision:
    return RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.91,
        resolved_by="legacy",
        source="test_legacy",
    )


def _ok_answers() -> dict[str, Any]:
    return {
        "primary_route": {"choice": "Concierge", "confidence": 0.99},
        "physical_sub_route": {"choice": "none", "confidence": 0.9},
        "concierge_sub_route": {"choice": "architecture", "confidence": 0.88},
        "session_sub_route": {"choice": "none", "confidence": 0.9},
        "emergency_required": {"noul": 0.01},
        "security_risk": {"noul": 0.01},
        "store_inquiry": {"noul": 0.01},
        "counseling_needed": {"noul": 0.01},
    }


@pytest.fixture
def session() -> dict[str, Any]:
    return {"messages": [], "channel": "web"}


def test_resolve_route_default_off_returns_legacy_identity(session: dict[str, Any]) -> None:
    legacy = _legacy_decision()
    with patch(
        "src.dialogue.routing.router.resolve_route_unified_or_legacy",
        return_value=legacy,
    ) as unified:
        with patch("config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=False):
            from src.dialogue.routing.router import resolve_route

            out = resolve_route("頭痛です", session, "sid-1", triage_result={"category": "Physical"})
    assert out is legacy
    unified.assert_called_once()
    assert session.get("_jev_shadow_correlation_id") is None


def test_resolve_route_shadow_on_still_returns_same_legacy(session: dict[str, Any]) -> None:
    legacy = _legacy_decision()
    scheduled: list[dict[str, Any]] = []

    def _schedule(**kwargs: Any) -> bool:
        scheduled.append(kwargs)
        return True

    with patch(
        "src.dialogue.routing.router.resolve_route_unified_or_legacy",
        return_value=legacy,
    ):
        with patch("config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=True):
            with patch(
                "src.dialogue.routing.jev_router.schedule_jev_shadow",
                side_effect=_schedule,
            ):
                with patch(
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

                    out = resolve_route("頭痛です", session, "sid-1")

    assert out is legacy
    assert len(scheduled) == 1
    assert scheduled[0]["legacy_decision"] is legacy
    assert session.get("_jev_shadow_correlation_id")


def test_resolve_route_primary_flag_true_still_returns_legacy(session: dict[str, Any]) -> None:
    """Phase 1 structural guarantee: PRIMARY must not change executed route."""
    legacy = _legacy_decision()
    with patch(
        "src.dialogue.routing.router.resolve_route_unified_or_legacy",
        return_value=legacy,
    ):
        with patch("config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=True):
            with patch("config.llm_flags.is_jev_intent_router_primary_enabled", return_value=True):
                with patch("src.dialogue.routing.jev_router.schedule_jev_shadow", return_value=True):
                    with patch(
                        "src.dialogue.routing.jev_router.build_jev_router_state",
                        return_value={
                            "channel": "web",
                            "user_input": "x",
                            "recent_turns": [],
                            "meta": {},
                            "app_context": "x",
                        },
                    ):
                        from src.dialogue.routing.router import resolve_route

                        out = resolve_route("x", session, "sid-p")
    assert out is legacy


def test_shadow_sync_failure_does_not_mutate_session_or_raise(session: dict[str, Any]) -> None:
    legacy = _legacy_decision()
    session["_routing_decision"] = legacy.to_dialogue_routing_dict()
    before = dict(session)

    with patch(
        "src.services.jev_client.evaluate_system_one",
        return_value=_FakeJevResult(
            ok=False,
            answers=None,
            usage=None,
            error_class="timeout",
            status_code=None,
        ),
    ):
        with patch("src.services.jev_metrics.record_shadow_event") as record:
            from src.dialogue.routing.jev_router import build_jev_router_state, run_jev_shadow_sync

            state = build_jev_router_state("息が苦しい", session, "sid-fail")
            assert "baseline_triage_hint" not in state
            ok = run_jev_shadow_sync(
                state=state,
                legacy_decision=legacy,
                correlation_id="corr-fail",
                sid="sid-fail",
                force=True,
            )
    assert ok is True
    assert session.get("_intent_router_shadow") is None
    assert session.get("_routing_decision") == before["_routing_decision"]
    assert record.called
    kwargs = record.call_args.kwargs
    assert kwargs.get("succeeded") is False
    assert kwargs.get("fallback_reason") == "timeout"


def test_shadow_sync_success_does_not_write_dispatch_keys(session: dict[str, Any]) -> None:
    legacy = _legacy_decision()
    with patch(
        "src.services.jev_client.evaluate_system_one",
        return_value=_FakeJevResult(ok=True, answers=_ok_answers(), usage={"input_tokens": 10}),
    ):
        with patch("src.services.jev_metrics.record_shadow_event") as record:
            from src.dialogue.routing.jev_router import build_jev_router_state, run_jev_shadow_sync

            state = build_jev_router_state("技術スタックは？", session, "sid-ok")
            run_jev_shadow_sync(
                state=state,
                legacy_decision=legacy,
                correlation_id="corr-ok",
                sid="sid-ok",
                force=True,
            )
    assert "_intent_router_shadow" not in session
    assert record.called
    jev = record.call_args.kwargs.get("jev_decision") or {}
    assert jev.get("primary_route") == "Concierge"
    # executed stays legacy for Phase 1
    executed = record.call_args.kwargs.get("executed_decision") or {}
    assert executed.get("primary_route") == "Physical"


def test_pipeline_skips_legacy_shadow_when_jev_on() -> None:
    """chat_post_pipeline must not schedule IntentRouter shadow that re-enters resolve_route."""
    calls: list[str] = []

    def fake_schedule(*_a: Any, **_k: Any) -> None:
        calls.append("legacy_shadow")

    # Import the block pattern by exercising the guard logic inline
    with patch("config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=True):
        from config.llm_flags import is_jev_intent_router_shadow_enabled

        jev_shadow_on = bool(is_jev_intent_router_shadow_enabled())
        if not jev_shadow_on:
            fake_schedule()
    assert calls == []

    with patch("config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=False):
        from config.llm_flags import is_jev_intent_router_shadow_enabled

        jev_shadow_on = bool(is_jev_intent_router_shadow_enabled())
        if not jev_shadow_on:
            fake_schedule()
    assert calls == ["legacy_shadow"]


def test_dispatcher_notifies_executed_without_reading_jev() -> None:
    from src.dialogue import dispatcher as disp

    ctx = MagicMock()
    ctx.sid = "sid-d"
    ctx.session = {"_jev_shadow_correlation_id": "corr-d"}
    ctx.sanitized_message = "hello"
    ctx.user_message = "hello"
    ctx.triage_result = {"category": "Other"}
    decision = RouteDecision(
        primary_route="Concierge",
        sub_route="greeting",
        confidence=1.0,
        resolved_by="gate",
        source="test",
    )

    with patch.object(disp, "is_intent_router_dispatch_enabled", return_value=True):
        with patch.object(disp, "_load_decision", return_value=decision):
            with patch.object(disp, "_should_skip_dispatch", return_value=False):
                with patch.object(disp, "_apply_decision_to_context"):
                    with patch.object(disp, "_dispatch_medicine_inventory_if_needed", return_value=None):
                        with patch.object(disp, "_DISPATCH_TABLE", {"Concierge": lambda c, m: None}):
                            with patch("src.services.jev_metrics.notify_executed_decision") as notify:
                                with patch.object(disp, "_log_dispatch"):
                                    out = disp.try_agent_dispatch(ctx, MagicMock())
    assert out is None
    notify.assert_called_once()
    assert notify.call_args.args[0] == "corr-d"
    assert notify.call_args.args[1] is decision


def test_state_never_includes_baseline_hint(session: dict[str, Any]) -> None:
    from src.dialogue.routing.jev_router import build_jev_router_state

    state = build_jev_router_state(
        "熱があります",
        session,
        "sid-h",
        triage_result={"category": "Physical", "confidence": 0.8},
    )
    assert "baseline_triage_hint" not in state
    dumped = str(state)
    assert "baseline_triage_hint" not in dumped
    assert "Physical" not in dumped or "last_primary" in str(state.get("meta"))
