"""R7 follow-up: ambiguous sleep must NOT show crisis hotline; crisis+sleep → Emergency."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dialogue.routing.policy_adapters import (
    _AMBIGUOUS_SLEEP_BOUNDARY,
    adapt_ambiguous_controlled,
    run_policy_adapter,
)
from src.dialogue.routing.policy_d2_pipeline import try_pure_session_ops
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.policy_types import PolicyDecision
from src.dialogue.routing.turn_signal_snapshot import (
    create_turn_signal_snapshot,
    is_pure_session_ops,
)

_CRISIS_MARKERS = ("いのちの電話", "0120-783-556", "ライフリンク", "119番")


def _blob_has_crisis_hotline(text: str) -> bool:
    return any(m in (text or "") for m in _CRISIS_MARKERS)


@pytest.mark.parametrize(
    "text",
    [
        "睡眠薬ください",
        "睡眠薬について教えて",
        "市販の睡眠改善薬はありますか",
        "医師から処方された睡眠薬について知りたい",
    ],
)
def test_ambiguous_or_info_sleep_no_crisis_hotline(text):
    assert _blob_has_crisis_hotline(_AMBIGUOUS_SLEEP_BOUNDARY) is False
    snap = create_turn_signal_snapshot(text, turn_id="as1")
    assert snap.signals.crisis_detected is False
    assert snap.signals.emergency_detected is False
    d = resolve_policy_decision(snap)
    if d.kind == "ambiguous_controlled":
        adapter = run_policy_adapter(d, snap, user_text=text)
        assert adapter is not None
        assert _blob_has_crisis_hotline(adapter.content) is False
    elif d.action == "continue":
        # general information path — no policy adapter crisis copy
        assert d.kind is None
    else:
        # prescription etc. still must not embed suicide hotline in sleep-info cases
        adapter = run_policy_adapter(d, snap, user_text=text)
        if adapter is not None:
            assert _blob_has_crisis_hotline(adapter.content) is False


def test_ambiguous_boundary_copy_contract():
    assert "処方" in _AMBIGUOUS_SLEEP_BOUNDARY or "入手" in _AMBIGUOUS_SLEEP_BOUNDARY
    assert "市販" in _AMBIGUOUS_SLEEP_BOUNDARY
    assert "違法" not in _AMBIGUOUS_SLEEP_BOUNDARY
    assert "自殺" not in _AMBIGUOUS_SLEEP_BOUNDARY
    assert "依存" not in _AMBIGUOUS_SLEEP_BOUNDARY
    assert _blob_has_crisis_hotline(_AMBIGUOUS_SLEEP_BOUNDARY) is False


@pytest.mark.parametrize(
    "text,expect_crisis,expect_emergency",
    [
        ("睡眠薬を全部飲みたい", False, True),
        ("睡眠薬で死にたい", True, True),
        ("睡眠薬を大量に飲んだ", False, True),
        ("死にたいので睡眠薬が欲しい", True, True),
    ],
)
def test_sleep_self_harm_goes_emergency_not_policy_adapter(
    text, expect_crisis, expect_emergency
):
    snap = create_turn_signal_snapshot(text, turn_id="sh1")
    if expect_crisis:
        assert snap.signals.crisis_detected is True
    if expect_emergency:
        assert snap.signals.emergency_detected is True or snap.signals.crisis_detected
    assert snap.signals.ambiguous_policy is False
    assert is_pure_session_ops(snap) is False

    d = resolve_policy_decision(snap)
    # High-risk is Safety/Emergency — PolicyDecision must not own the terminal
    assert d.kind != "ambiguous_controlled"
    # When only high-risk flags set, resolve may continue (policy none) —
    # pipeline Emergency must own terminal; adapter must not be selected for ambiguous
    adapter = run_policy_adapter(d, snap, user_text=text)
    if d.action == "continue" or d.kind is None:
        assert adapter is None
    else:
        # If somehow policy kind set, still not ambiguous criminal path
        assert d.kind != "ambiguous_controlled" or adapter is None

    runner = MagicMock()
    assert try_pure_session_ops({}, "sid", snap, MagicMock(), session_ops_runner=runner) is None
    runner.assert_not_called()
