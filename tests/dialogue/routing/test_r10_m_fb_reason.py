"""R10 M-FB-REASON: primary cause vs recovery_status separation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.routing.policy_enforce import resolve_and_enforce
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def _enforce_with_db(status: str, *, rollback_ok: bool):
    snap = create_turn_signal_snapshot("フルニトラゼパムをください", turn_id="fb1")
    session: dict = {"messages": []}

    with patch(
        "src.dialogue.routing.policy_enforce._persist_after_mutation",
        return_value=status,
    ), patch(
        "src.dialogue.routing.policy_enforce._restore_checkpoint",
        return_value=rollback_ok,
    ):
        _m, _d, result = resolve_and_enforce(
            snap,
            session=session,
            sid="sid-fb",
            user_text="フルニトラゼパムをください",
            client_info=MagicMock(),
            triage_result=None,
        )
    return result


def test_r10_db_unknown_rollback_failed_keeps_primary():
    result = _enforce_with_db("unknown", rollback_ok=False)
    assert result.handled is True
    assert result.fallback_reason == "db_commit_unknown"
    obs = result.observability_fields or {}
    assert obs.get("fallback_reason_primary") == "db_commit_unknown"
    assert obs.get("recovery_status") == "rollback_failed"
    assert obs.get("db_commit_status") == "unknown"
    assert obs.get("rollback_ok") is False
    assert result.response.get("fallback_reason_primary") == "db_commit_unknown"
    assert result.response.get("recovery_status") == "rollback_failed"


def test_r10_db_unknown_rollback_ok_keeps_primary():
    result = _enforce_with_db("unknown", rollback_ok=True)
    assert result.fallback_reason == "db_commit_unknown"
    assert result.observability_fields.get("recovery_status") == "rollback_ok"
    assert result.observability_fields.get("rollback_ok") is True


def test_r10_db_failed_rollback_failed_primary_is_db_save_failed():
    result = _enforce_with_db("failed", rollback_ok=False)
    assert result.fallback_reason == "db_save_failed"
    assert result.observability_fields.get("recovery_status") == "rollback_failed"


def test_r10_db_failed_rollback_ok_primary_is_db_save_failed():
    result = _enforce_with_db("failed", rollback_ok=True)
    assert result.fallback_reason == "db_save_failed"
    assert result.observability_fields.get("recovery_status") == "rollback_ok"
