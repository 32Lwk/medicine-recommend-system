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


def test_store_subcategory_not_medical_priority():
    triage = {
        "category": "Ask",
        "confidence": 0.9,
        "subcategory": "store_inquiry/inventory",
    }
    assert should_prioritize_medical_route_over_store(triage, "在庫ありますか") is False
