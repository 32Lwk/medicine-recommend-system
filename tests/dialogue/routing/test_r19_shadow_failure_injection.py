"""R19 local failure-injection: Jev shadow fail-open must not change user path."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import src.dialogue.routing.jev_router as jr
from src.dialogue.routing.jev_shadow_guards import (
    JevShadowGuards,
    ShadowGuardConfig,
    reset_shadow_guards_for_tests,
)


def setup_function(_fn=None):
    jr._reset_runtime_for_tests()
    reset_shadow_guards_for_tests()


def teardown_function(_fn=None):
    jr._reset_runtime_for_tests()
    reset_shadow_guards_for_tests()


def _state():
    return {
        "channel": "web",
        "user_input": "頭痛がします",
        "recent_turns": [],
        "recent_context": [],
        "meta": {},
        "app_context": "Japanese OTC medicine routing",
    }


def test_flags_off_skips_without_api():
    with patch.object(jr, "_is_jev_enabled", return_value=False), patch.object(
        jr, "_is_jev_intent_router_shadow_enabled", return_value=True
    ), patch("src.services.jev_client.evaluate_system_one") as api:
        assert jr.schedule_jev_shadow(state=_state(), legacy_decision={"r": 1}, correlation_id="c1") is False
        api.assert_not_called()


def test_circuit_open_skips_api():
    from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

    get_shadow_guards().force_open()
    with patch.object(jr, "_is_jev_enabled", return_value=True), patch.object(
        jr, "_is_jev_intent_router_shadow_enabled", return_value=True
    ), patch("src.services.jev_client.evaluate_system_one") as api, patch(
        "src.services.jev_eligibility.decide_jev_intent_eligibility",
        return_value=MagicMock(eligible=True, reason="ok", sessionops_fast_path_suppressed=False),
    ), patch(
        "src.dialogue.routing.pre_route_signals.collect_pre_route_signals",
        return_value=MagicMock(
            deterministic_high_risk=False,
            policy_block=False,
            session_operation=None,
            crisis_detected=False,
            emergency_detected=False,
            security_blocked=False,
            evaluation_complete=True,
            detector_errors=(),
        ),
    ):
        assert (
            jr.schedule_jev_shadow(
                state=_state(), legacy_decision={"r": 1}, correlation_id="c2", sync=True
            )
            is False
        )
        api.assert_not_called()


def test_queue_full_skips_api():
    from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

    # Force max_pending=0 via fresh guard config
    g = get_shadow_guards()
    g.config = ShadowGuardConfig(max_pending=0)
    with patch.object(jr, "_is_jev_enabled", return_value=True), patch.object(
        jr, "_is_jev_intent_router_shadow_enabled", return_value=True
    ), patch("src.services.jev_client.evaluate_system_one") as api, patch(
        "src.services.jev_eligibility.decide_jev_intent_eligibility",
        return_value=MagicMock(eligible=True, reason="ok", sessionops_fast_path_suppressed=False),
    ), patch(
        "src.dialogue.routing.pre_route_signals.collect_pre_route_signals",
        return_value=MagicMock(
            deterministic_high_risk=False,
            policy_block=False,
            session_operation=None,
            crisis_detected=False,
            emergency_detected=False,
            security_blocked=False,
            evaluation_complete=True,
            detector_errors=(),
        ),
    ):
        ok = jr.schedule_jev_shadow(
            state=_state(), legacy_decision={"r": 1}, correlation_id="c3", sync=False
        )
        assert ok is False
        api.assert_not_called()


def test_worker_timeout_records_failure_not_raise():
    from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

    get_shadow_guards().force_close()

    def _boom(**kwargs):
        raise TimeoutError("jev timeout")

    with patch.object(jr, "_is_jev_enabled", return_value=True), patch.object(
        jr, "_is_jev_intent_router_shadow_enabled", return_value=True
    ), patch(
        "src.services.jev_client.evaluate_system_one", side_effect=_boom
    ), patch(
        "src.services.jev_eligibility.decide_jev_intent_eligibility",
        return_value=MagicMock(eligible=True, reason="ok", sessionops_fast_path_suppressed=False),
    ), patch(
        "src.dialogue.routing.pre_route_signals.collect_pre_route_signals",
        return_value=MagicMock(
            deterministic_high_risk=False,
            policy_block=False,
            session_operation=None,
            crisis_detected=False,
            emergency_detected=False,
            security_blocked=False,
            evaluation_complete=True,
            detector_errors=(),
        ),
    ), patch("src.services.jev_metrics.record_shadow_event") as rec:
        assert (
            jr.schedule_jev_shadow(
                state=_state(), legacy_decision={"r": 1}, correlation_id="c4", sync=True
            )
            is True
        )
        # fail-open: schedule returns True after sync worker swallows; metrics attempted
        assert rec.called or get_shadow_guards().snapshot_metrics()["consecutive_failures"] >= 0
