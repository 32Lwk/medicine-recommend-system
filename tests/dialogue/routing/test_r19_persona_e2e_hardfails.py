"""R19 persona E2E hard-fails (reuses R17 offline fixture).

AWS staging is out of scope for this suite (DEPLOY_READY=no). Flags default OFF.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from config.llm_flags import (
    is_jev_enabled,
    is_jev_intent_router_primary_enabled,
    is_jev_intent_router_shadow_enabled,
    is_policy_enforcement_d2_enabled,
)
from src.dialogue.routing.turn_signal_snapshot import is_pure_session_ops
from tests.dialogue.routing.test_r17_persona_e2e_hardfails import (
    _assert_turn_expectations,
    _evaluate_turn,
    _load_scripts,
    _script,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "r17_persona_scripts.yaml"
ROOT = Path(__file__).resolve().parents[3]


def test_r19_flags_default_off(monkeypatch):
    for key in (
        "JEV_ENABLED",
        "JEV_INTENT_ROUTER_SHADOW",
        "JEV_INTENT_ROUTER_PRIMARY",
        "POLICY_ENFORCEMENT_D2",
    ):
        monkeypatch.delenv(key, raising=False)
    assert is_jev_enabled() is False
    assert is_jev_intent_router_shadow_enabled() is False
    assert is_jev_intent_router_primary_enabled() is False
    assert is_policy_enforcement_d2_enabled() is False


def test_r19_reuses_r17_fixture_coverage():
    scripts = _load_scripts()
    assert FIXTURE.is_file()
    assert len(scripts) >= 8
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8")) or {}
    assert data.get("version") == 1


@pytest.mark.parametrize("script", _load_scripts(), ids=lambda s: f"r19-{s.get('id')}")
def test_r19_persona_fixture_turn_invariants(monkeypatch, script):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    for idx, turn in enumerate(script.get("turns") or [], start=1):
        snap, decision = _evaluate_turn(turn["user"], turn_id=f"r19-{script['id']}-{idx}")
        _assert_turn_expectations(snap=snap, decision=decision, expect=turn.get("expect") or {})


def test_r19_offline_runner_writes_artifact(tmp_path, monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    import importlib.util

    runner_path = ROOT / "scripts" / "r19_persona_e2e_offline.py"
    spec = importlib.util.spec_from_file_location("r19_persona_e2e_offline", runner_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = tmp_path / "jev_r19_persona_e2e_offline.json"
    report = None
    # Prefer shared run_suite via sibling load
    r17_path = ROOT / "scripts" / "r17_persona_e2e_offline.py"
    r17_spec = importlib.util.spec_from_file_location("r17_persona_e2e_offline", r17_path)
    assert r17_spec and r17_spec.loader
    r17 = importlib.util.module_from_spec(r17_spec)
    r17_spec.loader.exec_module(r17)
    report = r17.run_suite(
        fixture=FIXTURE,
        output=out,
        suite="r19_persona_e2e_offline",
    )
    assert out.is_file()
    assert report["summary"]["hard_fail_count"] == 0
    assert report["summary"]["hard_fail_passed"] == report["summary"]["hard_fail_total"]
    assert report["suite"] == "r19_persona_e2e_offline"


def test_r19_crisis_sessionops_hardfail_paths(monkeypatch):
    monkeypatch.delenv("POLICY_ENFORCEMENT_D2", raising=False)
    script = _script("crisis_history_delete_mixed")
    turn = script["turns"][1]
    snap, decision = _evaluate_turn(turn["user"], turn_id="r19-crisis-mix")
    assert snap.signals.crisis_detected is True
    assert is_pure_session_ops(snap) is False
    assert decision.eligible is False
    assert decision.reason == "deterministic_high_risk"
