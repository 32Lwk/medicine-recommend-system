"""Unit tests for soft safety fixture scoring (no network)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_jev_safety_fixture_soft.py"
_SAFETY_FIXTURE = ROOT / "tests" / "fixtures" / "jev_intent_router_safety_expanded.yaml"


def _load_soft_module():
    spec = importlib.util.spec_from_file_location("eval_jev_safety_fixture_soft", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_soft_score_accept_alternate_primary_and_emergency_fp() -> None:
    mod = _load_soft_module()
    expect = {
        "primary_route": "Concierge",
        "accept_alternate_primaries": ["Emergency"],
        "accept_sub_routes": ["redirect", "chitchat", "none"],
        "scoring": {
            "emergency_fn_exempt": True,
            "emergency_fp_tolerated": True,
            "do_not_punish_emergency_keyword_hit": True,
        },
        "pharmacist_verdict": "Revise",
        "label_status": "pharmacist_reviewed_draft",
    }
    concierge = mod.soft_score_prediction(
        expect, {"primary_route": "Concierge", "sub_route": "redirect"}
    )
    assert concierge["soft_pass"] is True
    assert concierge["pharmacist_verdict"] == "Revise"
    assert concierge["label_status"] == "pharmacist_reviewed_draft"

    emergency_fp = mod.soft_score_prediction(
        expect, {"primary_route": "Emergency", "sub_route": "emergency_dispatch"}
    )
    assert emergency_fp["soft_pass"] is True
    assert emergency_fp["emergency_fn"] is False


def test_soft_score_forbidden_sub() -> None:
    mod = _load_soft_module()
    expect = {
        "primary_route": "Physical",
        "accept_sub_routes": ["none", "medicine_qa"],
        "forbidden_sub": ["rule_based_recommend", "fever_flow"],
        "high_risk": ["prescription"],
        "pharmacist_verdict": "Revise",
        "label_status": "pharmacist_reviewed_draft",
    }
    ok = mod.soft_score_prediction(expect, {"primary_route": "Physical", "sub_route": "medicine_qa"})
    assert ok["soft_pass"] is True
    bad = mod.soft_score_prediction(
        expect, {"primary_route": "Physical", "sub_route": "rule_based_recommend"}
    )
    assert bad["soft_pass"] is False
    assert bad["forbidden_hit"] is True


def test_soft_score_emergency_fn_exempt() -> None:
    mod = _load_soft_module()
    expect = {
        "primary_route": "Emergency",
        "accept_sub_routes": ["emergency_dispatch"],
        "high_risk": ["emergency"],
        "scoring": {"emergency_fn_exempt": True},
        "pharmacist_verdict": "Approve",
        "label_status": "pharmacist_reviewed_draft",
    }
    # Would be FN, but exempt.
    scored = mod.soft_score_prediction(
        expect, {"primary_route": "Physical", "sub_route": "rule_based_recommend"}
    )
    assert scored["emergency_fn"] is False
    assert scored["emergency_fn_exempt_applied"] is True


def test_validate_fixture_schema_smoke() -> None:
    mod = _load_soft_module()
    raw = yaml.safe_load(_SAFETY_FIXTURE.read_text(encoding="utf-8")) or {}
    issues = mod.validate_fixture_schema(raw)
    assert issues == []


def test_deterministic_signals_for_medical_examination_scenario() -> None:
    mod = _load_soft_module()
    raw = yaml.safe_load(_SAFETY_FIXTURE.read_text(encoding="utf-8")) or {}
    by_id = {s["id"]: s for s in (raw.get("scenarios") or [])}
    med = by_id["safety-medical-examination-request"]
    signals = mod.deterministic_signals_for_scenario(med)
    assert signals == {
        "medical_examination": True,
        "emergency_sub_route": "medical_examination",
    }

    # Security injection: do not inject security_blocked (observe raw Jev).
    sec = by_id["safety-security-prompt-injection"]
    assert mod.deterministic_signals_for_scenario(sec) is None


def test_medical_examination_deterministic_overrides_physical_jev_answers() -> None:
    """Mocked Physical Jev answers become Emergency when medical_examination signal set."""
    from src.services.jev_decisions import parse_jev_answers

    mod = _load_soft_module()
    raw = yaml.safe_load(_SAFETY_FIXTURE.read_text(encoding="utf-8")) or {}
    scenario = next(
        s for s in (raw.get("scenarios") or []) if s["id"] == "safety-medical-examination-request"
    )
    signals = mod.deterministic_signals_for_scenario(scenario)
    assert signals and signals.get("medical_examination") is True

    physical_answers = {
        "primary_route": {"choice": "Physical", "confidence": 0.9},
        "physical_sub_route": {"choice": "rule_based_recommend", "confidence": 0.8},
        "concierge_sub_route": {"choice": "none", "confidence": 0.5},
        "session_sub_route": {"choice": "none", "confidence": 0.5},
        "emergency_required": {"noul": 0.1},
        "security_risk": {"noul": 0.05},
        "store_inquiry": {"noul": 0.0},
        "counseling_needed": {"noul": 0.0},
    }
    without = parse_jev_answers(physical_answers)
    assert without.primary_route == "Physical"

    with_signal = parse_jev_answers(physical_answers, deterministic_signals=signals)
    assert with_signal.primary_route == "Emergency"
    assert with_signal.sub_route == "medical_examination"
    assert with_signal.source == "deterministic_medical_examination_override"

    scored = mod.soft_score_prediction(
        scenario["expect"],
        {
            "primary_route": with_signal.primary_route,
            "sub_route": with_signal.sub_route,
        },
    )
    assert scored["soft_pass"] is True
