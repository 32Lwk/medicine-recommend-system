"""R7-D/E: CheckpointEntry rollback + SF-E1-NM disabled."""
from __future__ import annotations

from unittest.mock import patch

from src.dialogue.routing.policy_enforce import (
    SF_E1_NM_ENABLED,
    build_sf_e1_response,
    enforce_policy_decision,
)
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_sf_e1_nm_disabled_flag():
    assert SF_E1_NM_ENABLED is False
    sage = build_sf_e1_response(no_mutation_claim=True)
    assert "変更されていません" not in (sage.get("message") or "")


def test_db_failed_empty_session_rollback_removes_new_keys():
    """Initial session without messages/inappropriate_requests; DB failed."""
    snap = create_turn_signal_snapshot("処方してください", turn_id="rb1")
    session: dict = {}  # no messages / inappropriate_requests keys

    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="failed",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="test-sid",
            user_text="処方してください",
        )

    assert result.handled is True
    assert "messages" not in session
    assert "inappropriate_requests" not in session
    msg = (result.response or {}).get("sage_diagnosis", {}).get("message", "")
    assert "変更されていません" not in msg
    # R21: typed boundary UX may replace SF-E1 on DB fail; session stays clean.
    assert result.observability_fields.get("safe_fallback") in (
        "SF-E1",
        "policy_boundary",
    )


def test_db_unknown_never_nm():
    snap = create_turn_signal_snapshot("処方してください", turn_id="rb2")
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="unknown",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="s",
            user_text="処方してください",
        )
    assert result.fallback_reason == "db_commit_unknown"
    assert result.observability_fields.get("fallback_reason_primary") == "db_commit_unknown"
    msg = (result.response or {}).get("sage_diagnosis", {}).get("message", "")
    assert "変更されていません" not in msg


def test_request_local_dedup_replay_not_exactly_once_claim():
    snap = create_turn_signal_snapshot("処方してください", turn_id="rb3")
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        r1 = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="s",
            user_text="処方してください",
        )
        count = len(session.get("messages", []))
        r2 = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="s",
            user_text="処方してください",
        )
    assert r1.handled and r2.handled
    assert r2.observability_fields.get("request_local_dedup_replay") is True
    assert "idempotent_replay" not in (r2.observability_fields or {})
    assert len(session.get("messages", [])) == count
