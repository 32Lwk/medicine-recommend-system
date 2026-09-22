"""BR-H02: past-tense / hypothetical crisis FN fixtures."""
from __future__ import annotations

import pytest

from src.core.crisis_detection import detect_crisis_keywords
from src.dialogue.routing.gate import run_deterministic_gate


BR_H02_PAST_OR_HYP = (
    "昔は死にたかった",
    "昨日は本気で死にたかった",
    "もし死にたくなったらどうすればいい",
)


@pytest.mark.parametrize("text", BR_H02_PAST_OR_HYP)
def test_br_h02_past_or_hyp_is_crisis(text: str) -> None:
    has, _ = detect_crisis_keywords(text)
    assert has, f"FN: {text!r}"


def test_br_h02_simple_negation_still_tn() -> None:
    has, _ = detect_crisis_keywords("今は死にたくない")
    assert not has


def test_br_h02_counseling_past_ideation_emergency() -> None:
    text = "昔は死にたかった"
    d = run_deterministic_gate(
        text, {"counseling_mode": {"active": True}, "messages": []}, "br-h02"
    )
    assert d.primary_route == "Emergency"
