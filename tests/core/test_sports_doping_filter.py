"""Tests for sports doping candidate filter."""
from __future__ import annotations

import pytest


def test_doping_filter_excludes_prohibited(monkeypatch):
    monkeypatch.setenv("RECO_SPORTS_DOPING_FILTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)

    candidates = [
        {"product_name": "A", "doping_prohibited": "禁止物質あり"},
        {"product_name": "B", "doping_prohibited": "禁止物質なし"},
    ]
    from src.services.medicine_discovery_routing import has_sports_medicine_context

    assert has_sports_medicine_context("水泳大会前")
    filtered = [
        c
        for c in candidates
        if str(c.get("doping_prohibited") or "").strip() != "禁止物質あり"
    ]
    assert len(filtered) == 1
    assert filtered[0]["product_name"] == "B"


@pytest.mark.parametrize(
    "user_text,expected_status",
    [
        ("水泳大会前に使える薬", "escalation_required"),
    ],
)
def test_rule_based_sports_doping_zero_escalates(user_text, expected_status, monkeypatch):
    monkeypatch.setenv("RECO_SPORTS_DOPING_FILTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)

    candidates = [
        c
        for c in [{"product_name": "X", "doping_prohibited": "禁止物質あり"}]
        if str(c.get("doping_prohibited") or "").strip() != "禁止物質あり"
    ]
    assert candidates == []

    from src.services.medicine_discovery_routing import has_sports_medicine_context

    assert has_sports_medicine_context(user_text)
    assert expected_status == "escalation_required"

