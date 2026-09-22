"""R10 M-OBS: D2 telemetry matches log_counseling_detail contract."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.routing.policy_d2_pipeline import try_policy_enforcement_d2
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_r10_m_obs_log_counseling_detail_receives_required_args():
    snap = create_turn_signal_snapshot("睡眠薬ください", turn_id="obs1")
    session: dict = {"messages": []}
    recorded: list = []

    def _capture(session_id, user_input, response, conversation_history=None, **kwargs):
        recorded.append(
            {
                "session_id": session_id,
                "user_input": user_input,
                "response": response,
                "routing_meta": kwargs.get("routing_meta"),
            }
        )

    with patch(
        "src.utils.structured_logger.log_counseling_detail", side_effect=_capture
    ), patch(
        "src.handlers.chat.chat_input_validator._persist_block_messages_to_db",
    ):
        resp = try_policy_enforcement_d2(
            session,
            "sid-obs",
            snap,
            user_text="睡眠薬ください",
            client_info=MagicMock(),
            triage_result=None,
        )

    assert resp is not None
    assert len(recorded) == 1
    row = recorded[0]
    assert row["user_input"] == "[policy_enforcement_d2]"
    assert row["response"] == "[redacted]"
    meta = row["routing_meta"] or {}
    assert meta.get("policy_enforcement_d2") is True
    assert meta.get("policy_kind") == "ambiguous_controlled"
    assert meta.get("handled") is True
    assert meta.get("turn_id")
    assert "fingerprint" in meta
    # No raw medical text leaked into meta keys of concern
    assert "睡眠薬" not in str(meta)


def test_r10_m_obs_logger_exception_does_not_fail_user_path():
    snap = create_turn_signal_snapshot("睡眠薬ください", turn_id="obs2")
    session: dict = {"messages": []}

    with patch(
        "src.utils.structured_logger.log_counseling_detail",
        side_effect=RuntimeError("log boom"),
    ):
        resp = try_policy_enforcement_d2(
            session,
            "sid-obs2",
            snap,
            user_text="睡眠薬ください",
            client_info=MagicMock(),
            triage_result=None,
        )
    assert resp is not None
    assert resp[1] == 200
