"""Unit tests for eval_jev_intent_router_10 helpers (no network)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_jev_intent_router_10.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("eval_jev_intent_router_10", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_summarize_excludes_connection_errors_from_accuracy() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 100.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
        },
        {
            "backend": "current",
            "pass": False,
            "error": "APIConnectionError",
            "outcome": "api_error",
            "connection_error": True,
            "transport_ok": False,
        },
        {
            "backend": "current",
            "pass": False,
            "latency_ms": 200.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
        },
    ]
    summary = mod._summarize(results, "current")
    assert summary["attempted"] == 3
    assert summary["api_error"] == 1
    assert summary["connection_error"] == 1
    assert summary["scored"] == 2
    assert summary["passed"] == 1
    assert summary["accuracy_pct"] == 50.0


def test_bootstrap_latency_ci_paired() -> None:
    mod = _load_mod()
    pairs = [(1000.0, 500.0), (1200.0, 520.0), (900.0, 480.0)]
    ci = mod._bootstrap_latency_diff_ci(pairs, n_boot=200)
    assert ci["available"] is True
    assert ci["mean_diff_ms"] > 0
    assert ci["ci95_low_ms"] <= ci["ci95_high_ms"]


def test_minimal_state_has_no_baseline_hint() -> None:
    mod = _load_mod()
    scenario = {"id": "x", "input": "頭痛", "setup": ["こんにちは"], "channel": "web"}
    state = mod._jev_state(
        scenario,
        mode="minimal",
        current_result={"triage_result": {"category": "Ask"}},
    )
    assert "recent_turns" in state
    assert "recent_context" in state
    assert state["recent_turns"] is state["recent_context"]
    assert "baseline_triage_hint" not in state


def test_disagreement_joint() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "scenario_id": "a",
            "run_idx": 0,
            "actual_primary": "Physical",
            "actual_sub": "medicine_qa",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "a",
            "run_idx": 0,
            "actual_primary": "Physical",
            "actual_sub": "rule_based_recommend",
            "pass": True,
            "outcome": "ok",
        },
    ]
    disag = mod._collect_disagreements(results)
    assert len(disag) == 1
    assert disag[0]["sub_disagree"] is True
    assert disag[0]["primary_disagree"] is False


def test_disagreement_ignores_sub_route_aliases() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "scenario_id": "jev-emergency-breathing",
            "run_idx": 0,
            "actual_primary": "Emergency",
            "actual_sub": "chest_pain_breathing_difficulty",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "jev-emergency-breathing",
            "run_idx": 0,
            "actual_primary": "Emergency",
            "actual_sub": "emergency_dispatch",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "current",
            "scenario_id": "jev-session-delete",
            "run_idx": 0,
            "actual_primary": "SessionOps",
            "actual_sub": "delete",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "jev-session-delete",
            "run_idx": 0,
            "actual_primary": "SessionOps",
            "actual_sub": "delete_confirm",
            "pass": True,
            "outcome": "ok",
        },
    ]
    assert mod._collect_disagreements(results) == []
