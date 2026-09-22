"""Integration: POLICY_ENFORCEMENT_D2 flag OFF/ON wiring smoke."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_flag_off_skips_d2_snapshot_path(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    from config.llm_flags import is_policy_enforcement_d2_enabled

    assert is_policy_enforcement_d2_enabled() is False


def test_flag_on_enables(monkeypatch):
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "1")
    # re-import flag reader path
    from config import llm_flags

    assert llm_flags.is_policy_enforcement_d2_enabled() is True
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)


def test_follow_ups_skip_policy_kinds_fail_closed_residual():
    from src.handlers.chat.chat_triage_follow_ups import run_triage_follow_ups

    session = {"messages": []}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    early, detected = run_triage_follow_ups(
        session,
        client,
        "sid",
        "処方してください",
        "処方してください",
        "処方してください",
        {"category": "Other", "subcategory": "inappropriate_request/prescription"},
        MagicMock(),
        skip_policy_kinds=True,
    )
    assert detected is True
    assert early is not None
    body, code = early
    assert code == 200
    assert body.get("fallback_reason") == "residual_policy_after_d2_continue"
    assert "変更されていません" not in (
        (body.get("sage_diagnosis") or {}).get("message") or ""
    )
    # Exactly one SF-E1 bot notice; no counseling/drug template duplication
    assert len(session["messages"]) == 1


def test_triage_bag_maps_policy_without_session_ops_rewrite():
    from src.dialogue.routing.policy_d2_pipeline import triage_to_additive_bag
    from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot

    snap = create_turn_signal_snapshot("履歴を要約して", turn_id="i1")
    before = snap.signals.session_operation
    bag = triage_to_additive_bag(
        {"category": "Other", "subcategory": "inappropriate_request/prescription"}
    )
    merged = snap.with_additive(bag)
    assert merged.signals.prescription_block is True
    assert merged.signals.session_operation == before
