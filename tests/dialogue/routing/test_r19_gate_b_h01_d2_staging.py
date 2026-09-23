"""R19 Gate B H-01: D2 ON staging boundaries; default remains OFF."""
from __future__ import annotations

from unittest.mock import patch

from config.llm_flags import is_policy_enforcement_d2_enabled
from src.dialogue.routing.policy_enforce import enforce_policy_decision, resolve_and_enforce
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_policy_enforcement_d2_default_remains_off(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert is_policy_enforcement_d2_enabled() is False


def test_d2_on_prescription_boundary_terminal(monkeypatch):
    """When D2 is ON (staging), prescription PolicyDecision yields boundary UX."""
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    assert is_policy_enforcement_d2_enabled() is True

    snap = create_turn_signal_snapshot("処方箋が必要な薬を処方して", turn_id="h01-rx")
    d = resolve_policy_decision(snap)
    assert d.kind == "prescription"
    assert d.action == "boundary_guidance"

    session: dict = {"messages": [], "pending_memory_delete": False}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        result = enforce_policy_decision(
            d,
            snap,
            session=session,
            sid="sid-h01",
            user_text="処方箋が必要な薬を処方して",
        )
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert result.handled is True
    assert result.policy_kind == "prescription"
    assert result.fallback_reason is None
    assert len(session.get("messages", [])) >= 1
    # SessionOps-style keys must not be flipped by prescription boundary
    assert session.get("pending_memory_delete") is False


def test_d2_on_medical_examination_boundary(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    snap = create_turn_signal_snapshot(
        "病院で診てもらった方がいいか診断してください。病気名を教えて",
        turn_id="h01-exam",
    )
    d = resolve_policy_decision(snap)
    assert d.kind == "medical_examination"

    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        _m, _d, result = resolve_and_enforce(
            snap,
            session=session,
            sid="sid-exam",
            user_text="診断してください",
        )
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert result.handled is True
    assert result.policy_kind == "medical_examination"
