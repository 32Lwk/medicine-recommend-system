"""IntentRouter shadow テスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.dialogue.routing.shadow import run_and_record_shadow


@patch("src.dialogue.routing.shadow.is_intent_router_v2_enabled", return_value=True)
def test_shadow_records_routing(_enabled):
    session: dict = {"messages": []}
    triage = {"category": "Physical", "confidence": 0.99, "subcategory": "fever"}
    decision = run_and_record_shadow(session, "line:U1", "39度の熱", triage)
    assert decision is not None
    assert decision.primary_route == "Physical"
    assert session.get("dialogue_state", {}).get("routing", {}).get("primary_route") == "Physical"
    assert "_intent_router_shadow" in session


@patch("src.dialogue.routing.shadow.is_intent_router_v2_enabled", return_value=False)
def test_shadow_skipped_when_flag_off(_enabled):
    session: dict = {}
    assert run_and_record_shadow(session, "line:U1", "頭痛い", {}) is None


def test_mismatch_session_ops_with_session_admin():
    from src.dialogue.routing.shadow import _mismatch
    from src.dialogue.routing.types import RouteDecision

    decision = RouteDecision(
        primary_route="SessionOps",
        sub_route="delete",
        confidence=1.0,
        resolved_by="gate",
    )
    triage = {"category": "Other", "subcategory": "session_admin", "session_intent": "delete"}
    assert _mismatch(decision, triage) is False


def test_mismatch_ask_physical_agrees():
    from src.dialogue.routing.shadow import _mismatch
    from src.dialogue.routing.types import RouteDecision

    decision = RouteDecision(primary_route="Physical", confidence=0.9, resolved_by="gate")
    triage = {"category": "Ask", "confidence": 0.8}
    assert _mismatch(decision, triage) is False


def test_mismatch_pending_cancelled_physical_not_mismatch():
    from src.dialogue.routing.shadow import _mismatch
    from src.dialogue.routing.types import RouteDecision

    session = {
        "dialogue_state": {
            "version": 1,
            "flags": {"pending_cancelled_by_physical": True},
        }
    }
    decision = RouteDecision(primary_route="Physical", confidence=0.95, resolved_by="gate")
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.5}
    assert _mismatch(decision, triage, session) is False


def test_mismatch_fever_context_physical_not_mismatch():
    from src.dialogue.routing.shadow import _mismatch
    from src.dialogue.routing.types import RouteDecision

    session = {
        "dialogue_state": {
            "version": 1,
            "flags": {"fever_context": True},
        }
    }
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="fever_flow",
        confidence=0.9,
        resolved_by="guard",
    )
    triage = {"category": "Other", "subcategory": "general_other", "confidence": 0.5}
    assert _mismatch(decision, triage, session) is False


@patch("src.dialogue.routing.shadow.is_intent_router_v2_enabled", return_value=True)
def test_shadow_logs_dialogue_flags(_enabled):
    session = {
        "messages": [],
        "dialogue_state": {
            "version": 1,
            "flags": {"fever_context": True},
        },
    }
    with patch("src.dialogue.routing.shadow.log_dialogue_route_shadow") as mock_log:
        run_and_record_shadow(session, "line:U1", "近くの薬局", {"category": "Other"})
    assert mock_log.called
    assert mock_log.call_args.kwargs.get("dialogue_flags") == {"fever_context": True}
