"""Physical/Ask トリアージと店舗ゲートの優先度"""
from src.services.store_inquiry_handler import (
    has_unambiguous_store_intent,
    is_probable_store_inquiry,
)
from src.utils.input_helpers import should_prioritize_medical_route_over_store


def test_physical_medicine_discovery_skips_store_gate():
    triage = {"category": "Physical", "confidence": 0.9, "subcategory": "cold"}
    assert should_prioritize_medical_route_over_store(triage, "風邪薬を教えて") is True
    assert is_probable_store_inquiry("風邪薬ありますか", triage) is False


def test_ask_medicine_discovery_skips_store_gate():
    triage = {"category": "Ask", "confidence": 0.85, "subcategory": "medication_query"}
    assert should_prioritize_medical_route_over_store(triage, "風邪薬ありますか") is True
    assert is_probable_store_inquiry("風邪薬ありますか", triage) is False


def test_toilet_still_store_despite_ask_triage():
    triage = {"category": "Ask", "confidence": 0.8, "subcategory": "general_other"}
    assert should_prioritize_medical_route_over_store(triage, "トイレどこ？") is False
    assert has_unambiguous_store_intent("トイレどこ？") is True
    assert is_probable_store_inquiry("トイレどこ？", triage) is True


def test_explicit_store_inventory_not_medical_priority():
    triage = {"category": "Physical", "confidence": 0.9, "subcategory": "cold"}
    text = "風邪薬の在庫ありますか"
    assert should_prioritize_medical_route_over_store(triage, text) is False
    assert is_probable_store_inquiry(text, triage) is True


def test_fever_symptom_prioritizes_medical_over_store():
    triage = {"category": "Physical", "confidence": 0.99, "subcategory": "fever"}
    text = "39度の熱があります"
    assert should_prioritize_medical_route_over_store(triage, text) is True
    assert is_probable_store_inquiry(text, triage) is False
    assert has_unambiguous_store_intent(text) is False


def test_fever_session_context_blocks_store_after_fever_turn():
    session = {
        "messages": [
            {"type": "user", "content": "39度の熱があります"},
            {"type": "bot", "content": "ok"},
        ]
    }
    triage = {"category": "Other", "confidence": 0.5, "subcategory": "general_other"}
    assert should_prioritize_medical_route_over_store(
        triage, "近くの薬局", session=session
    ) is True
    from src.services.routing_context import RoutingContext, evaluate_store_gate

    routing_ctx = RoutingContext.build(
        session, "line:U1", "近くの薬局", triage_result=triage
    )
    assert (
        evaluate_store_gate(
            "近くの薬局",
            triage_result=triage,
            routing_ctx=routing_ctx,
        )
        is False
    )


def test_fever_dialogue_state_flag_blocks_store():
    session = {
        "dialogue_state": {"version": 1, "flags": {"fever_context": True}},
        "messages": [],
    }
    triage = {"category": "Other", "confidence": 0.5, "subcategory": "general_other"}
    assert should_prioritize_medical_route_over_store(
        triage, "トイレどこ？", session=session
    ) is True


def test_store_subcategory_not_medical_priority():
    triage = {
        "category": "Ask",
        "confidence": 0.9,
        "subcategory": "store_inquiry/inventory",
    }
    assert should_prioritize_medical_route_over_store(triage, "在庫ありますか") is False
