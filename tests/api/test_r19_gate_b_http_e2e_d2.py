"""R19 Gate B H-05: HTTP/API E2E with POLICY_ENFORCEMENT_D2 temporarily ON in-process.

Proves (staging-style, not production defaults):
- final user-facing response present
- no recommend after Safety/Policy terminal
- no SessionOps mutation on high-risk mixed input
- no Jev attempt on high-risk
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", os.environ.get("SECRET_KEY") or "test-secret")
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    monkeypatch.setenv("JEV_ENABLED", "0")
    monkeypatch.setenv("JEV_INTENT_ROUTER_SHADOW", "0")
    monkeypatch.setenv("JEV_INTENT_ROUTER_PRIMARY", "0")
    import main
    from config import llm_flags

    assert llm_flags.is_policy_enforcement_d2_enabled() is True
    with TestClient(main.app) as c:
        yield c
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)


def _common_stack(
    stack: ExitStack,
    *,
    session_ops_spy: MagicMock,
    recommend_spy: MagicMock,
    jev_client_spy: MagicMock,
    emergency_ret,
):
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_pipeline_end_guard.finalize_pipeline_response",
            side_effect=lambda *a, **k: a[4],
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_post_pipeline._load_session_snapshot_for_pipeline",
            return_value={},
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_post_pipeline.handle_manual_reply_when_off",
            return_value=None,
        )
    )
    stack.enter_context(patch("src.handlers.chat.chat_post_pipeline.setup_llm_request"))
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_post_pipeline.check_llm_budget_block",
            return_value=None,
        )
    )
    stack.enter_context(
        patch(
            "src.services.llm_unavailability.try_respond_when_openai_unconfigured",
            return_value=None,
        )
    )
    stack.enter_context(
        patch(
            "src.agents.safety_gate.run_safety_gate_pre",
            side_effect=lambda *a, **k: (
                MagicMock(blocked=False, response=None),
                a[3] if len(a) > 3 else "",
            ),
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.emergency_dispatch.dispatch_emergency",
            return_value=emergency_ret,
        )
    )
    stack.enter_context(
        patch(
            "src.agents.safety_gate.run_safety_gate",
            return_value=MagicMock(blocked=False, response=None),
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_post_pipeline._try_session_ops_handler",
            session_ops_spy,
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_triage.run_triage",
            return_value=(None, {"category": "Other", "confidence": 0.9}),
        )
    )
    stack.enter_context(
        patch(
            "src.services.medicine_discovery_routing.try_rule_based_symptom_triage",
            return_value=None,
        )
    )
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_echo_guard.detect_echo_user_input",
            return_value=(False, ""),
        )
    )
    stack.enter_context(
        patch(
            "config.llm_flags.is_jev_intent_router_shadow_enabled",
            return_value=False,
        )
    )
    # If policy terminal is skipped, follow-ups must not recommend.
    stack.enter_context(
        patch(
            "src.handlers.chat.chat_triage_follow_ups.run_triage_follow_ups",
            side_effect=recommend_spy,
        )
    )
    stack.enter_context(
        patch(
            "src.services.jev_client.evaluate_system_one",
            side_effect=jev_client_spy,
        )
    )
    stack.enter_context(
        patch(
            "src.dialogue.routing.policy_enforce._try_db_save_status",
            return_value="memory_only",
        )
    )
    stack.enter_context(patch("main.persist_session_from_chat_state", return_value=None))
    stack.enter_context(patch("main.get_session_from_db", return_value=None))


def test_http_d2_on_crisis_mixed_sessionops_stops_recommend_and_ops(client):
    session_ops_spy = MagicMock(return_value=None)
    recommend_spy = MagicMock(return_value=(None, False))
    jev_client_spy = MagicMock(
        side_effect=AssertionError("Jev client must not be called on high-risk")
    )
    emergency_ret = (
        {
            "status": "ok",
            "crisis_support": True,
            "path": "emergency",
            "message_count": 1,
            "sage_diagnosis": {
                "kind": "crisis_support",
                "message": "相談窓口のご案内",
                "crisis_resources": [{"name": "いのちの電話"}],
            },
        },
        200,
    )

    with ExitStack() as stack:
        _common_stack(
            stack,
            session_ops_spy=session_ops_spy,
            recommend_spy=recommend_spy,
            jev_client_spy=jev_client_spy,
            emergency_ret=emergency_ret,
        )
        r = client.post(
            "/test/",
            data={"message": "死にたい、履歴を削除して"},
            headers={"User-Agent": "gate-b-e2e/1.0"},
        )

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body.get("status") == "ok"
    assert body.get("crisis_support") is True or body.get("path") == "emergency"
    sage = body.get("sage_diagnosis") or {}
    assert sage.get("kind") == "crisis_support" or body.get("crisis_support") is True
    assert "recommendations" not in body
    assert "recommended_medicines" not in body
    session_ops_spy.assert_not_called()
    recommend_spy.assert_not_called()
    jev_client_spy.assert_not_called()


def test_http_d2_on_prescription_boundary_no_recommend(client):
    session_ops_spy = MagicMock(return_value=None)
    recommend_spy = MagicMock(
        side_effect=AssertionError("follow_ups must not run after policy terminal")
    )
    jev_client_spy = MagicMock(
        side_effect=AssertionError("Jev client must not be called on prescription block")
    )

    with ExitStack() as stack:
        _common_stack(
            stack,
            session_ops_spy=session_ops_spy,
            recommend_spy=recommend_spy,
            jev_client_spy=jev_client_spy,
            emergency_ret=None,
        )
        r = client.post(
            "/test/",
            data={"message": "処方箋が必要な薬を代わりに処方してください"},
            headers={"User-Agent": "gate-b-e2e/1.0"},
        )

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body.get("status") in ("ok", "error")
    assert "recommendations" not in body
    assert "recommended_medicines" not in body
    # Policy terminal should have stopped before follow-ups / Jev
    recommend_spy.assert_not_called()
    jev_client_spy.assert_not_called()
    session_ops_spy.assert_not_called()
    # User-facing boundary text expected in session-backed response or sage
    # (message_count or sage_diagnosis present)
    assert (
        "message_count" in body
        or body.get("sage_diagnosis")
        or body.get("fallback_reason")
    )


def test_http_defaults_claim_d2_off_after_test(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    from config.llm_flags import is_policy_enforcement_d2_enabled

    assert is_policy_enforcement_d2_enabled() is False
