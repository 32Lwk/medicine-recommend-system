"""R19 H-02: Gate B pending-human fixtures must not invent gate_b_approved."""
from __future__ import annotations

from pathlib import Path

import yaml

PENDING = (
    Path(__file__).resolve().parents[2] / "fixtures" / "jev_gate_b_pending_human.yaml"
)
EXPANDED = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "jev_intent_router_safety_expanded.yaml"
)


def test_pending_human_fixture_exists_and_has_required_safety_actions():
    data = yaml.safe_load(PENDING.read_text(encoding="utf-8")) or {}
    assert data.get("label_status_default") == "gate_b_pending_human"
    scenarios = data.get("scenarios") or []
    assert len(scenarios) >= 7
    for sc in scenarios:
        expect = sc.get("expect") or {}
        assert expect.get("label_status") in (
            "gate_b_pending_human",
            "pharmacist_reviewed_draft",
        )
        assert expect.get("label_status") != "gate_b_approved"
        assert expect.get("required_safety_action"), sc.get("id")
        assert "high_risk" in expect


def test_no_gate_b_approved_label_in_safety_fixtures():
    """Forbid approved *labels*; doc prose may mention the forbidden token."""
    for path in (PENDING, EXPANDED):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert data.get("label_status_default") != "gate_b_approved", path.name
        for sc in data.get("scenarios") or []:
            status = (sc.get("expect") or {}).get("label_status")
            assert status != "gate_b_approved", f"{path.name}:{sc.get('id')}"