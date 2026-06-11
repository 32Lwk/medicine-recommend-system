"""processing_agent_display"""
from src.services.processing_agent_display import slow_hint_for_phase, user_agent_display


def test_user_agent_display_uses_agent_name():
    s = user_agent_display("SafetyGate", "safety", "contra_check", "physical")
    assert s == "担当: SafetyGate"


def test_user_agent_display_medicine_qa():
    s = user_agent_display("MedicineQAAgent", "medicine_qa", "answer_compose", "ask_qa")
    assert s == "担当: MedicineQAAgent"


def test_slow_hint_llm_classify():
    h = slow_hint_for_phase("physical", "symptom_analysis", "llm_classify")
    assert h is not None
    assert "お待ち" in h


def test_slow_hint_none_for_fast_step():
    assert slow_hint_for_phase("physical", "symptom_analysis", "symptom_extract") is None
