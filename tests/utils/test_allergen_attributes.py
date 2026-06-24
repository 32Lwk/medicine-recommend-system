"""allergen_attributes / persist マージのテスト"""
from src.utils.allergen_attributes import (
    extract_environmental_allergens_from_message,
    is_otc_allergy_consultation_entry,
    merge_chat_user_attributes,
    merge_list_attribute,
    normalize_environmental_allergens,
)


def test_extract_pollen_from_message():
    out = extract_environmental_allergens_from_message("花粉症です")
    assert out["allergies"] == ["花粉"]
    assert "medical_history" not in out


def test_normalize_moves_pollen_from_medical_history():
    attrs = {"medical_history": ["花粉症"], "allergies": []}
    normalized = normalize_environmental_allergens(attrs)
    assert normalized["allergies"] == ["花粉"]
    assert normalized["medical_history"] == []


def test_merge_chat_user_attributes_unions_lists():
    db = {"allergies": ["花粉"], "medical_history": []}
    session = {"allergies": [], "age": 30}
    merged = merge_chat_user_attributes(db, session)
    assert merged["age"] == 30
    assert merged["allergies"] == ["花粉"]


def test_merge_chat_user_attributes_strips_legacy_pollen_history():
    db = {"allergies": [], "medical_history": ["花粉症"]}
    session = {"allergies": [], "medical_history": []}
    merged = merge_chat_user_attributes(db, session)
    assert merged["allergies"] == ["花粉"]
    assert merged["medical_history"] == []


def test_is_otc_allergy_consultation_entry():
    assert is_otc_allergy_consultation_entry("花粉症です") is True
    assert is_otc_allergy_consultation_entry("花粉症で鼻水がひどい") is False


def test_merge_list_attribute_unions_without_overwrite():
    merged, changed = merge_list_attribute(["糖尿病"], ["花粉症"])
    assert changed is True
    assert merged == ["糖尿病", "花粉症"]
