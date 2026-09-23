"""Smoke: local failure-injection rehearsal exits 0 (no AWS)."""
from __future__ import annotations

import runpy
from pathlib import Path


def test_shadow_failure_injection_local_script_exits_zero(monkeypatch):
    monkeypatch.setenv("JEV_ENABLED", "false")
    monkeypatch.setenv("JEV_INTENT_ROUTER_SHADOW", "false")
    monkeypatch.setenv("JEV_INTENT_ROUTER_PRIMARY", "false")
    monkeypatch.setenv("POLICY_ENFORCEMENT_D2", "false")
    monkeypatch.delenv("JEV_API_KEY", raising=False)

    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "jev_shadow_failure_injection_local.py"
    )
    ns = runpy.run_path(str(script), run_name="__not_main__")
    assert ns["main"]() == 0
