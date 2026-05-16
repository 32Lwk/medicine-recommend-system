"""processing_flows ユニットテスト"""
from src.services.processing_flows import (
    compute_progress,
    flow_for_triage_category,
    get_flow_steps,
    pick_label,
)


def test_greeting_flow_steps():
    steps = get_flow_steps("greeting")
    assert steps == ["validate", "triage", "counseling", "finalize"]
    step, total, percent = compute_progress("greeting", "counseling")
    assert total == 4
    assert step == 3
    assert percent > 0


def test_pick_label_deterministic():
    a = pick_label("ask_qa", "medicine_qa", "sess-a")
    b = pick_label("ask_qa", "medicine_qa", "sess-a")
    c = pick_label("ask_qa", "medicine_qa", "sess-b")
    assert a == b
    assert isinstance(c, str)


def test_flow_for_category():
    assert flow_for_triage_category("Ask") == "ask_qa"
    assert flow_for_triage_category("Physical") == "physical"
