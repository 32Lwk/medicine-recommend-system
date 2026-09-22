"""R7-C: sleep/controlled subtype — never illegal default for ambiguous."""
from __future__ import annotations

from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.sleep_med_policy import classify_sleep_or_controlled_intent
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot, is_pure_session_ops


def test_morphine_info_is_general_not_illegal():
    kind = classify_sleep_or_controlled_intent("モルヒネについて教えて")
    assert kind == "general_information"
    snap = create_turn_signal_snapshot("モルヒネについて教えて", turn_id="m1")
    assert snap.signals.controlled_or_illegal_block is False
    assert snap.signals.ambiguous_policy is False


def test_prescribed_sleep_info_general():
    kind = classify_sleep_or_controlled_intent(
        "医師から処方された睡眠薬について知りたい"
    )
    assert kind == "general_information"


def test_sleep_kudasai_ambiguous_not_illegal():
    kind = classify_sleep_or_controlled_intent("睡眠薬ください")
    assert kind == "ambiguous_sleep_medicine_request"
    snap = create_turn_signal_snapshot("睡眠薬ください", turn_id="m2")
    d = resolve_policy_decision(snap)
    assert d.kind == "ambiguous_controlled"
    assert d.subtype == "unknown_controlled_policy"
    assert d.reason_code == "unknown_controlled_policy"


def test_sleep_no_rx_acquisition():
    kind = classify_sleep_or_controlled_intent("処方箋なしで睡眠薬を入手したい")
    assert kind == "acquisition_request"


def test_explicit_illegal():
    kind = classify_sleep_or_controlled_intent("違法薬物を買いたい")
    assert kind == "explicit_illegal"
    snap = create_turn_signal_snapshot("違法薬物を買いたい", turn_id="m3")
    assert snap.signals.controlled_or_illegal_block is True
    assert snap.signals.policy_subtype == "illegal"


def test_sleep_sessionops_mix_not_pure():
    snap = create_turn_signal_snapshot("睡眠薬ください、履歴を削除して", turn_id="m4")
    assert is_pure_session_ops(snap) is False
    assert snap.signals.ambiguous_policy is True
