"""R7 C2: CheckpointEntry rollback integration — empty session + failed/unknown/rollback fail."""
from __future__ import annotations

from unittest.mock import patch

from src.dialogue.routing.policy_enforce import (
    CheckpointEntry,
    SessionCheckpoint,
    _REQUEST_LOCAL_DEDUP_KEY,
    _build_checkpoint,
    _restore_checkpoint,
    enforce_policy_decision,
)
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def _assert_no_nm(result) -> None:
    msg = (result.response or {}).get("sage_diagnosis", {}).get("message", "")
    assert "変更されていません" not in msg
    # R21 F-H03-R2: typed PolicyDecision may surface boundary UX instead of SF-E1
    # on DB failure, but must never claim NM / durable mutation success.
    assert result.observability_fields.get("safe_fallback") in (
        "SF-E1",
        "policy_boundary",
    )


def test_c2_db_failed_empty_session_deep_equality_clean():
    snap = create_turn_signal_snapshot("処方してください", turn_id="c2a")
    session: dict = {}
    checkpoint = _build_checkpoint(session)

    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="failed",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="sid",
            user_text="処方してください",
        )

    assert result.handled is True
    assert "messages" not in session
    assert "inappropriate_requests" not in session
    assert "illegal_drug_block" not in session
    assert "counseling_mode" not in session
    assert _REQUEST_LOCAL_DEDUP_KEY not in session
    assert "_policy_enforcement_d2_receipt" not in session
    assert checkpoint.deep_equals_session(session) is True
    _assert_no_nm(result)


def test_c2_db_unknown_empty_session():
    snap = create_turn_signal_snapshot("処方してください", turn_id="c2b")
    session: dict = {}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="unknown",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="sid",
            user_text="処方してください",
        )
    assert result.fallback_reason == "db_commit_unknown"
    assert result.observability_fields.get("fallback_reason_primary") == "db_commit_unknown"
    assert "messages" not in session or result.observability_fields.get("rollback_ok") is False
    # On successful rollback, keys must be gone
    if result.observability_fields.get("rollback_ok"):
        assert "messages" not in session
        assert "inappropriate_requests" not in session
        assert _REQUEST_LOCAL_DEDUP_KEY not in session
    _assert_no_nm(result)


def test_c2_rollback_failure_forbids_nm_and_alerts_path():
    snap = create_turn_signal_snapshot("処方してください", turn_id="c2c")
    session: dict = {}

    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="failed",
    ), patch(
        "src.dialogue.routing.policy_enforce._restore_checkpoint",
        return_value=False,
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="sid",
            user_text="処方してください",
        )
    assert result.fallback_reason == "db_save_failed"
    assert result.observability_fields.get("recovery_status") == "rollback_failed"
    _assert_no_nm(result)
    assert result.observability_fields.get("rollback_ok") is False


def test_checkpoint_entry_absent_keys_removed_on_restore():
    session = {"messages": [{"type": "bot", "content": "x"}], "illegal_drug_block": True}
    cp = SessionCheckpoint(
        entries={
            "messages": CheckpointEntry(existed=False, value=None),
            "inappropriate_requests": CheckpointEntry(existed=False, value=None),
            "counseling_mode": CheckpointEntry(existed=False, value=None),
            "illegal_drug_block": CheckpointEntry(existed=False, value=None),
            "pending_memory_delete": CheckpointEntry(existed=False, value=None),
            "counseling_symptom_type": CheckpointEntry(existed=False, value=None),
            "counseling_questions": CheckpointEntry(existed=False, value=None),
            _REQUEST_LOCAL_DEDUP_KEY: CheckpointEntry(existed=False, value=None),
            "_policy_enforcement_d2_receipt": CheckpointEntry(existed=False, value=None),
        },
        modified_existed=False,
        modified_value=None,
    )
    assert _restore_checkpoint(session, cp) is True
    assert "messages" not in session
    assert "illegal_drug_block" not in session
    assert cp.deep_equals_session(session) is True
