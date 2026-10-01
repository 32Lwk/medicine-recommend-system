"""Jev PRIMARY — Stage B（OpenAI）を Jev 判定で置き換え、採用不可時のみ OpenAI へ戻す。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from src.dialogue.routing.types import RouteDecision


@dataclass
class _FakeJevResult:
    ok: bool
    answers: dict[str, Any] | None
    usage: dict[str, Any] | None = None
    latency_ms: float = 1.0
    retry_count: int = 0
    error_class: str | None = None
    status_code: int | None = 200
    model: str = "jev-latest"
    resolved_version: str | None = None


def _answers(primary: str = "Physical", conf: float = 0.95, **noul: float) -> dict[str, Any]:
    return {
        "primary_route": {"choice": primary, "confidence": conf},
        "physical_sub_route": {"choice": "rule_based_recommend", "confidence": 0.9},
        "concierge_sub_route": {"choice": "none", "confidence": 0.9},
        "session_sub_route": {"choice": "none", "confidence": 0.9},
        "emergency_required": {"noul": noul.get("emergency", 0.01)},
        "security_risk": {"noul": noul.get("security", 0.01)},
        "store_inquiry": {"noul": 0.01},
        "counseling_needed": {"noul": 0.01},
    }


_OPENAI = RouteDecision(
    primary_route="Concierge",
    sub_route="chitchat",
    confidence=0.8,
    resolved_by="legacy",
    source="openai_stage_b",
)


@pytest.fixture(autouse=True)
def _reset_guards():
    from src.dialogue.routing.jev_shadow_guards import reset_shadow_guards_for_tests

    reset_shadow_guards_for_tests()
    yield
    reset_shadow_guards_for_tests()


def _resolve(jev_result: Any, *, primary_on: bool = True) -> tuple[RouteDecision, int]:
    calls: list[int] = []

    def _openai(*_a: Any, **_k: Any) -> RouteDecision:
        calls.append(1)
        return _OPENAI

    with patch(
        "config.llm_flags.is_jev_intent_router_primary_enabled", return_value=primary_on
    ), patch(
        "src.services.jev_client.evaluate_system_one", return_value=jev_result
    ), patch(
        "src.dialogue.routing.legacy_router.run_deterministic_gate", return_value=None
    ), patch(
        "src.dialogue.routing.legacy_router.run_intent_router_llm", side_effect=_openai
    ), patch(
        "src.dialogue.routing.legacy_router.apply_post_route_guards",
        side_effect=lambda d, *_a, **_k: d,
    ), patch(
        "src.services.jev_metrics.record_shadow_event"
    ):
        from src.dialogue.routing.legacy_router import resolve_legacy_route

        out = resolve_legacy_route("頭痛がします", {"messages": []}, "sid-1")
    return out, len(calls)


def test_primary_on_adopts_jev_and_skips_openai() -> None:
    out, openai_calls = _resolve(_FakeJevResult(ok=True, answers=_answers()))
    assert out.resolved_by == "jev"
    assert out.primary_route == "Physical"
    assert out.sub_route == "rule_based_recommend"
    assert openai_calls == 0


def test_primary_off_uses_openai() -> None:
    out, openai_calls = _resolve(_FakeJevResult(ok=True, answers=_answers()), primary_on=False)
    assert out is _OPENAI
    assert openai_calls == 1


def test_jev_failure_falls_back_to_openai() -> None:
    out, openai_calls = _resolve(
        _FakeJevResult(ok=False, answers=None, error_class="timeout", status_code=None)
    )
    assert out is _OPENAI
    assert openai_calls == 1


def test_low_confidence_falls_back_to_openai() -> None:
    out, openai_calls = _resolve(_FakeJevResult(ok=True, answers=_answers(conf=0.4)))
    assert out is _OPENAI
    assert openai_calls == 1


def test_jev_emergency_is_not_confirmed_alone() -> None:
    out, openai_calls = _resolve(
        _FakeJevResult(ok=True, answers=_answers(emergency=0.95))
    )
    assert out is _OPENAI
    assert openai_calls == 1


def test_high_confidence_gate_never_calls_jev() -> None:
    gate = RouteDecision(
        primary_route="Emergency",
        sub_route="emergency_dispatch",
        confidence=1.0,
        resolved_by="gate",
        source="gate_test",
    )
    with patch(
        "config.llm_flags.is_jev_intent_router_primary_enabled", return_value=True
    ), patch("src.services.jev_client.evaluate_system_one") as jev, patch(
        "src.dialogue.routing.legacy_router.run_deterministic_gate", return_value=gate
    ), patch(
        "src.dialogue.routing.legacy_router.apply_post_route_guards",
        side_effect=lambda d, *_a, **_k: d,
    ):
        from src.dialogue.routing.legacy_router import resolve_legacy_route

        out = resolve_legacy_route("胸が痛くて息ができない", {"messages": []}, "sid-1")
    assert out is gate
    jev.assert_not_called()


def test_router_skips_shadow_when_primary_on() -> None:
    legacy = RouteDecision(primary_route="Physical", resolved_by="jev", source="jev")
    session: dict[str, Any] = {"messages": []}
    with patch(
        "src.dialogue.routing.router.resolve_route_unified_or_legacy", return_value=legacy
    ), patch(
        "config.llm_flags.is_jev_intent_router_shadow_enabled", return_value=True
    ), patch(
        "config.llm_flags.is_jev_intent_router_primary_enabled", return_value=True
    ), patch("src.dialogue.routing.jev_router.schedule_jev_shadow") as schedule:
        from src.dialogue.routing.router import resolve_route

        out = resolve_route("頭痛です", session, "sid-1")
    assert out is legacy
    schedule.assert_not_called()
    assert session.get("_jev_shadow_correlation_id") is None
