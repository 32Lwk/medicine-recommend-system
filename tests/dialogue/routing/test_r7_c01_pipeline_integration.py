"""R7 C1: full run_chat_post_pipeline integration with POLICY_ENFORCEMENT_D2=ON."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.utils.chat_http_context import ChatClientInfo


def test_d2_on_zw_crisis_full_pipeline_emergency_once_no_sessionops_jev_reco(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    from config import llm_flags

    assert llm_flags.is_policy_enforcement_d2_enabled() is True

    session = {"messages": []}
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    user_text = "死\u200bにたい、履歴を削除して"
    emergency_calls: list = []

    def _emergency(*args, **kwargs):
        emergency_calls.append({"args": args, "kwargs": kwargs})
        return ({"status": "ok", "path": "emergency", "message_count": 1}, 200)

    session_ops = MagicMock(return_value=None)
    policy_adapter = MagicMock()

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
        side_effect=_emergency,
    ), patch(
        "src.handlers.chat.chat_post_pipeline._try_session_ops_handler",
        session_ops,
    ), patch(
        "src.dialogue.routing.policy_adapters.run_policy_adapter",
        policy_adapter,
    ), patch(
        "config.llm_flags.is_jev_intent_router_shadow_enabled",
        return_value=False,
    ), patch(
        "src.handlers.chat.chat_echo_guard.detect_echo_user_input",
        return_value=(False, ""),
    ):
        from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

        body, status = run_chat_post_pipeline(
            session, client, user_text, "sid-c1", MagicMock()
        )

    assert status == 200
    assert body.get("path") == "emergency"
    assert len(emergency_calls) == 1
    detect_arg = emergency_calls[0]["args"][3]
    assert "\u200b" not in detect_arg
    assert "死にたい" in detect_arg
    session_ops.assert_not_called()
    policy_adapter.assert_not_called()
    assert "pending_memory_delete" not in session
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
