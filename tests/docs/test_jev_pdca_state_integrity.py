"""PDCA state integrity: cycle_count_valid matches valid cycle records."""
from __future__ import annotations

import json
from pathlib import Path

REQUIRED_CYCLE_FIELDS = (
    "cycle_id",
    "sequence",
    "category",
    "hypothesis",
    "target_metric",
    "files_changed",
    "tests_run",
    "independent_review",
    "medical_review",
    "result",
    "regression",
    "residual_risks",
    "next_action",
    "gate_status",
)

STATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "planning"
    / "codex-parallel-jev-20260921"
    / "JEV_AUTONOMOUS_PDCA_STATE.json"
)


def test_pdca_state_cycles_complete_and_unique() -> None:
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    cycles = data.get("cycles") or []
    valid_results = {
        "accepted",
        "rejected",
        "revised",
        "invalid",
    }
    valid = [c for c in cycles if str(c.get("result") or "").lower() in valid_results]
    assert data["cycle_count_valid"] == len(valid)
    ids = [c["cycle_id"] for c in valid]
    seqs = [c["sequence"] for c in valid]
    assert len(ids) == len(set(ids))
    assert len(seqs) == len(set(seqs))
    for c in valid:
        for field in REQUIRED_CYCLE_FIELDS:
            assert field in c, f"missing {field} in {c.get('cycle_id')}"
