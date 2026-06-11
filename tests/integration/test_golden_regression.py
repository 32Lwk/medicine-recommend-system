"""ゴールデンケース JSONL のオフライン検証"""
from __future__ import annotations

import json
import os
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from tests._paths import FIXTURES_DIR

GOLDEN_DIR = FIXTURES_DIR / "golden"


def _load_jsonl(name: str):
    path = os.path.join(GOLDEN_DIR, name)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@pytest.mark.parametrize(
    "case",
    _load_jsonl("sample_cases.jsonl")
    or [{"input_text": "x", "expected_category": "Other"}],
)
def test_golden_schema_fields(case):
    assert case.get("input_text")
    assert case.get("expected_category") in (
        "Physical",
        "Emotional",
        "Emergency",
        "Ask",
        "Other",
    )


def test_golden_sample_count_40():
    cases = _load_jsonl("sample_cases.jsonl")
    assert len(cases) >= 40


def test_golden_category_ratio():
    """P16/E10/A6/Em4/O4 内訳（6/1マイルストーン）"""
    cases = _load_jsonl("sample_cases.jsonl")
    if len(cases) < 40:
        pytest.skip("sample_cases.jsonl not fully populated")
    c = Counter(x["expected_category"] for x in cases)
    assert c["Physical"] >= 16
    assert c["Emotional"] >= 10
    assert c["Ask"] >= 6
    assert c["Emergency"] >= 4
    assert c["Other"] >= 4


@patch("src.services.llm_triage.llm_triage")
def test_golden_triage_mock_category(mock_triage):
    cases = _load_jsonl("sample_cases.jsonl")[:5]
    if not cases:
        pytest.skip("no golden cases")
    for case in cases:
        mock_triage.return_value = {
            "category": case["expected_category"],
            "confidence": 0.9,
        }
        from src.agents.triage_agent import run_triage_agent

        result = run_triage_agent(case["input_text"], MagicMock(), use_cache=False)
        assert result["category"] == case["expected_category"]
