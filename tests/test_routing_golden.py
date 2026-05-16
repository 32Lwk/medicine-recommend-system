"""ルーティングゴールデンセット（高速・オフライン部分）"""
import json
from pathlib import Path

import pytest

from src.services.concierge_intent import classify_concierge_intent

FIXTURE = Path(__file__).parent / "fixtures" / "routing_golden.jsonl"


def _load_cases():
    cases = []
    with FIXTURE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


@pytest.mark.parametrize("case", _load_cases())
def test_fast_concierge_classifier(case):
    text = case["input"]
    if case.get("meaningless"):
        pytest.skip("meaningless cases use ConfidenceGate")
    expected_fast = case.get("expected_fast_concierge")
    if expected_fast:
        assert classify_concierge_intent(text) == expected_fast
    if case.get("not_concierge_intent"):
        assert classify_concierge_intent(text) != case["not_concierge_intent"]
    if case.get("expected_category") == "Ask":
        assert classify_concierge_intent(text) is None
