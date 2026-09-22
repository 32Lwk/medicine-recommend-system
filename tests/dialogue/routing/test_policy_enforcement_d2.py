"""Unit tests: PolicyDecision resolve + content-only adapters + enforce."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dialogue.routing.policy_adapters import (
    adapt_prescription,
    run_policy_adapter,
)
from src.dialogue.routing.policy_enforce import (
    build_sf_e1_response,
    enforce_policy_decision,
    resolve_and_enforce,
)
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.policy_types import PolicyDecision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_resolve_priority_controlled_over_prescription():
    snap = create_turn_signal_snapshot("x", turn_id="p1")
    merged = snap.with_additive(
        {"controlled_or_illegal_block": True, "prescription_block": True}
    )
    d = resolve_policy_decision(merged)
    assert d.kind == "controlled_or_illegal"
    assert d.action == "block"


def test_resolve_prescription():
    snap = create_turn_signal_snapshot("処方してください", turn_id="p2")
    d = resolve_policy_decision(snap)
    assert d.kind == "prescription"
    assert d.action == "boundary_guidance"


def test_resolve_continue_no_hit():
    snap = create_turn_signal_snapshot("今日は天気がいい", turn_id="p3")
    d = resolve_policy_decision(snap)
    assert d.action == "continue"
    assert d.kind is None


def test_adapter_prescription_no_session_mutation():
    session = {"messages": []}
    snap = create_turn_signal_snapshot("処方してください", turn_id="p4")
    d = resolve_policy_decision(snap)
    result = adapt_prescription(d, snap, user_text="処方してください")
    assert "処方" in result.content or "処方箋" in result.content
    assert session["messages"] == []  # adapter must not mutate
    assert result.observability.get("llm_used") is False


def test_adapter_unknown_kind_none():
    snap = create_turn_signal_snapshot("x", turn_id="p5")
    d = PolicyDecision(
        kind=None,
        action="continue",
        detector_source="none",
        confidence=1.0,
        reason_code="no_policy_hit",
        evaluation_complete=True,
    )
    assert run_policy_adapter(d, snap, user_text="x") is None


def test_incomplete_evaluation_safe_fallback():
    snap = create_turn_signal_snapshot("x", turn_id="p6")
    from dataclasses import replace

    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            evaluation_complete=False,
            detector_errors=("detector_boom",),
        ),
    )
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text="x"
    )
    assert result.handled is True
    assert result.fallback_reason == "incomplete_evaluation"
    assert result.observability_fields.get("safe_fallback") == "SF-E1"
    assert "変更されていません" not in (
        (result.response or {}).get("sage_diagnosis", {}).get("message") or ""
    )


def test_enforce_prescription_terminal(monkeypatch):
    snap = create_turn_signal_snapshot("処方してください", turn_id="p7")
    session: dict = {"messages": []}

    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="test-sid",
            user_text="処方してください",
        )
    assert result.handled is True
    assert result.policy_kind == "prescription"
    assert len(session.get("messages", [])) >= 1
    assert "fingerprint" in result.observability_fields


def test_db_commit_unknown_forbids_nm():
    snap = create_turn_signal_snapshot("処方してください", turn_id="p8")
    session: dict = {"messages": []}

    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="unknown",
    ):
        result = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="test-sid",
            user_text="処方してください",
        )
    assert result.handled is True
    assert result.fallback_reason == "db_commit_unknown"
    assert result.observability_fields.get("fallback_reason_primary") == "db_commit_unknown"
    assert result.observability_fields.get("safe_fallback") == "SF-E1"
    msg = (result.response or {}).get("sage_diagnosis", {}).get("message", "")
    assert "変更されていません" not in msg


def test_idempotent_receipt_replay():
    snap = create_turn_signal_snapshot("処方してください", turn_id="p9")
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
        count_after = len(session.get("messages", []))
        r2 = enforce_policy_decision(
            resolve_policy_decision(snap),
            snap,
            session=session,
            sid="s",
            user_text="処方してください",
        )
    assert r1.handled and r2.handled
    assert r2.observability_fields.get("request_local_dedup_replay") is True
    assert len(session.get("messages", [])) == count_after


def test_flag_default_off():
    from config.llm_flags import is_policy_enforcement_d2_enabled

    import os

    if not os.environ.get("POLICY_ENFORCEMENT_D2"):
        assert is_policy_enforcement_d2_enabled() is False


def test_sf_e1_nm_suffix():
    base = build_sf_e1_response(no_mutation_claim=False)
    nm = build_sf_e1_response(no_mutation_claim=True)
    # R7-E: NM disabled — both are SF-E1
    assert "変更されていません" not in (base.get("message") or "")
    assert "変更されていません" not in (nm.get("message") or "")
    assert "救急" not in (nm.get("message") or "")
    assert "違法" not in (nm.get("message") or "")