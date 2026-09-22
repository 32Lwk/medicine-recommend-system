"""R8-B: POLICY_ENFORCEMENT_D2 OFF/ON via run_chat_post_pipeline."""
from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from src.dialogue.routing import policy_d2_pipeline as d2p
from src.utils.chat_http_context import ChatClientInfo


def _run_post_pipeline(
    *,
    user_text: str,
    emergency_ret=None,
    session_ops_ret=None,
    snapshot_spy: list | None = None,
    policy_spy: list | None = None,
):
    session: dict = {"messages": []}
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    real_create = d2p.create_pipeline_snapshot

    def _snap(*a, **k):
        if snapshot_spy is not None:
            snapshot_spy.append(1)
        return real_create(*a, **k)

    with ExitStack() as stack:
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
                return_value=(MagicMock(blocked=False, response=None), user_text),
            )
        )
        stack.enter_context(
            patch(
                "src.handlers.chat.chat_emergency_handler.handle_emergency_if_detected",
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
                return_value=session_ops_ret,
            )
        )
        stack.enter_context(
            patch(
                "src.handlers.chat.chat_triage.run_triage",
                return_value={"category": "Other", "confidence": 0.9},
            )
        )
        stack.enter_context(
            patch(
                "src.services.medicine_discovery_routing.try_rule_based_symptom_triage",
                return_value={"category": "Other", "confidence": 0.9},
            )
        )
        stack.enter_context(
            patch(
                "config.llm_flags.is_jev_intent_router_shadow_enabled",
                return_value=False,
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
                "src.dialogue.routing.policy_d2_pipeline.create_pipeline_snapshot",
                side_effect=_snap,
            )
        )
        if policy_spy is not None:
            real_tp = d2p.try_policy_enforcement_d2

            def _tp(*a, **k):
                policy_spy.append(1)
                return real_tp(*a, **k)

            stack.enter_context(
                patch(
                    "src.dialogue.routing.policy_d2_pipeline.try_policy_enforcement_d2",
                    side_effect=_tp,
                )
            )

        from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

        body, status = run_chat_post_pipeline(
            session, client, user_text, "sid-r8b", MagicMock()
        )
    return body, status, session


def test_r8_flag_off_no_snapshot_no_d2_policy(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "0")
    from config import llm_flags

    assert llm_flags.is_policy_enforcement_d2_enabled() is False

    snapshot_spy: list = []
    policy_spy: list = []
    session_ops_body = ({"status": "ok", "path": "session_ops", "message_count": 1}, 200)
    body, status, _ = _run_post_pipeline(
        user_text="履歴を削除して",
        emergency_ret=None,
        session_ops_ret=session_ops_body,
        snapshot_spy=snapshot_spy,
        policy_spy=policy_spy,
    )
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert status == 200
    assert body.get("path") == "session_ops"
    assert snapshot_spy == []
    assert policy_spy == []


def test_r8_flag_on_snapshot_once_pure_session_ops(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    from config import llm_flags

    assert llm_flags.is_policy_enforcement_d2_enabled() is True

    snapshot_spy: list = []
    policy_spy: list = []
    session_ops_body = ({"status": "ok", "path": "session_ops", "message_count": 1}, 200)
    body, status, _ = _run_post_pipeline(
        user_text="履歴を削除して",
        emergency_ret=None,
        session_ops_ret=session_ops_body,
        snapshot_spy=snapshot_spy,
        policy_spy=policy_spy,
    )
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert status == 200
    assert body.get("path") == "session_ops"
    assert len(snapshot_spy) == 1
    assert policy_spy == []


def test_r8_flag_on_mixed_crisis_blocks_session_ops(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    snapshot_spy: list = []
    emerg = ({"status": "ok", "path": "emergency", "message_count": 1}, 200)
    session: dict = {"messages": []}
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    user_text = "死にたい、履歴を削除して"
    session_ops = MagicMock(return_value=None)
    real_create = d2p.create_pipeline_snapshot

    def _snap(*a, **k):
        snapshot_spy.append(1)
        return real_create(*a, **k)

    with patch(
        "src.handlers.chat.chat_pipeline_end_guard.finalize_pipeline_response",
        side_effect=lambda *a, **k: a[4],
    ), patch(
        "src.handlers.chat.chat_post_pipeline._load_session_snapshot_for_pipeline",
        return_value={},
    ), patch(
        "src.handlers.chat.chat_post_pipeline.handle_manual_reply_when_off",
        return_value=None,
    ), patch(
        "src.handlers.chat.chat_post_pipeline.setup_llm_request",
    ), patch(
        "src.handlers.chat.chat_post_pipeline.check_llm_budget_block",
        return_value=None,
    ), patch(
        "src.services.llm_unavailability.try_respond_when_openai_unconfigured",
        return_value=None,
    ), patch(
        "src.agents.safety_gate.run_safety_gate_pre",
        return_value=(MagicMock(blocked=False, response=None), user_text),
    ), patch(
        "src.handlers.chat.chat_emergency_handler.handle_emergency_if_detected",
        return_value=emerg,
    ), patch(
        "src.handlers.chat.chat_post_pipeline._try_session_ops_handler",
        session_ops,
    ), patch(
        "config.llm_flags.is_jev_intent_router_shadow_enabled",
        return_value=False,
    ), patch(
        "src.handlers.chat.chat_echo_guard.detect_echo_user_input",
        return_value=(False, ""),
    ), patch(
        "src.dialogue.routing.policy_d2_pipeline.create_pipeline_snapshot",
        side_effect=_snap,
    ):
        from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

        body, status = run_chat_post_pipeline(
            session, client, user_text, "sid-mix", MagicMock()
        )

    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert status == 200
    assert body.get("path") == "emergency"
    assert len(snapshot_spy) == 1
    session_ops.assert_not_called()
