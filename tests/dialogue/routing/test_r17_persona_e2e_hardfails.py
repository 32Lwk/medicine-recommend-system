"""R17 overnight persona E2E: offline hard-fail routing invariants."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from config.llm_flags import is_policy_enforcement_d2_enabled
from src.dialogue.routing.turn_signal_snapshot import (
    create_turn_signal_snapshot,
    is_pure_session_ops,
)
from src.services.jev_eligibility import decide_jev_intent_eligibility

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "r17_persona_scripts.yaml"


def _load_scripts() -> list[dict]:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8")) or {}
    scripts = data.get("scripts") or []
    assert isinstance(scripts, list) and scripts
    return scripts


def _script(script_id: str) -> dict:
    for script in _load_scripts():
        if script.get("id") == script_id:
            return script
    raise AssertionError(f"script not found: {script_id}")


def _evaluate_turn(user_text: str, *, turn_id: str):
    snap = create_turn_signal_snapshot(user_text, turn_id=turn_id)
    decision = decide_jev_intent_eligibility(snap.signals)
    return snap, decision


def _assert_turn_expectations(*, snap, decision, expect: dict) -> None:
    scalar_checks = {
        "emergency_detected": snap.signals.emergency_detected,
        "crisis_detected": snap.signals.crisis_detected,
        "security_blocked": snap.signals.security_blocked,
        "medical_examination": snap.signals.medical_examination,
        "prescription_block": snap.signals.prescription_block,
        "controlled_or_illegal_block": snap.signals.controlled_or_illegal_block,
        "ambiguous_policy": snap.signals.ambiguous_policy,
        "policy_block": snap.signals.policy_block,
        "deterministic_high_risk": snap.signals.deterministic_high_risk,
        "evasion_fail_closed": snap.signals.evasion_fail_closed,
        "detector_view_had_evasion": snap.detector_view_had_evasion,
        "session_operation": snap.signals.session_operation,
        "pure_session_ops": is_pure_session_ops(snap),
        "eligible": decision.eligible,
        "eligibility_reason": decision.reason,
    }
    for key, actual in scalar_checks.items():
        if key in expect:
            assert actual == expect[key], f"{key}: expected={expect[key]!r} actual={actual!r}"

    for needle in expect.get("detector_text_contains") or []:
        assert needle in snap.detector_text
    for needle in expect.get("detector_text_not_contains") or []:
        assert needle not in snap.detector_text


def test_r17_fixture_has_minimum_multiturn_coverage():
    scripts = _load_scripts()
    assert len(scripts) >= 8
    for script in scripts:
        turns = script.get("turns") or []
        assert 3 <= len(turns) <= 8, script.get("id")
        assert all(str(turn.get("user") or "").strip() for turn in turns)
        assert all(isinstance(turn.get("expect") or {}, dict) for turn in turns)


def test_r17_defaults_keep_d2_off(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    assert is_policy_enforcement_d2_enabled() is False


@pytest.mark.parametrize("script", _load_scripts(), ids=lambda s: str(s.get("id")))
def test_r17_persona_fixture_turn_invariants(monkeypatch, script):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)

    for idx, turn in enumerate(script.get("turns") or [], start=1):
        snap, decision = _evaluate_turn(turn["user"], turn_id=f"{script['id']}-{idx}")
        _assert_turn_expectations(snap=snap, decision=decision, expect=turn.get("expect") or {})


def test_zero_width_crisis_evasion_uses_detector_view(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    script = _script("zero_width_crisis_evasion")
    turn = script["turns"][1]
    snap, decision = _evaluate_turn(turn["user"], turn_id="zw-crisis")

    assert snap.signals.crisis_detected is True
    assert snap.detector_view_had_evasion is True
    assert snap.signals.evasion_fail_closed is True
    assert "\u200b" not in snap.detector_text
    assert "死にたい" in snap.detector_text
    assert is_pure_session_ops(snap) is False
    assert decision.eligible is False
    assert decision.reason == "deterministic_high_risk"


def test_ambiguous_sleep_med_is_policy_not_criminal(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    script = _script("ambiguous_sleep_med_not_criminal")
    turn = script["turns"][1]
    snap, decision = _evaluate_turn(turn["user"], turn_id="sleep-ambiguous")

    assert snap.signals.ambiguous_policy is True
    assert snap.signals.controlled_or_illegal_block is False
    assert snap.signals.session_operation == "delete"
    assert is_pure_session_ops(snap) is False
    assert decision.reason == "policy_block"


def test_elderly_short_physical_stays_local_eligible(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    script = _script("elderly_short_sentence_physical")

    for idx, turn in enumerate(script["turns"], start=1):
        snap, decision = _evaluate_turn(turn["user"], turn_id=f"elderly-{idx}")
        assert snap.signals.deterministic_high_risk is False
        assert snap.signals.policy_block is False
        assert snap.signals.session_operation_detected is False
        assert is_pure_session_ops(snap) is False
        assert decision.eligible is True
        assert decision.reason == "intent_classification_candidate"
