"""
安全性回帰（赤チームプロンプト50件）— エージェント経路含む
"""
from __future__ import annotations

import json
import os

import pytest

from src.agents.protocols import emergency_handoff
from src.agents.triage_agent import keyword_pre_triage, resolve_handoff
from src.agents.tools.recommendation_tool import as_tool_schema
from tests._paths import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "safety" / "red_team.jsonl"


def _load_red_team():
    if not os.path.exists(FIXTURE):
        return []
    rows = []
    with open(FIXTURE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@pytest.mark.parametrize("case", _load_red_team() or [{"prompt": "x", "expected_handoff_not": "PhysicalOrchestrator"}])
def test_red_team_not_physical_handoff(case):
    prompt = case["prompt"]
    triage = {"category": "Other", "subcategory": "inappropriate_request", "confidence": 0.9}
    handoff = resolve_handoff(triage, prompt, {})
    assert handoff.target != case.get("expected_handoff_not", "PhysicalOrchestrator")


def test_keyword_pre_triage_emergency():
    r = keyword_pre_triage("胸が痛くて息ができない")
    assert r is not None
    assert r["category"] == "Emergency"


def test_emergency_handoff_stops():
    h = emergency_handoff("chest pain")
    assert h.stop is True
    assert h.target == "EmergencyHandler"


def test_tool_schema_rule_based():
    schema = as_tool_schema()
    assert schema["name"] == "rule_based_medicine_recommendation"
    assert "user_text" in schema["parameters"]["required"]


def test_red_team_fixture_count():
    cases = _load_red_team()
    assert len(cases) >= 50
