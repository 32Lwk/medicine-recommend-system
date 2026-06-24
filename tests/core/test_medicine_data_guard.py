"""medicine_data の防御的ガード"""
from src.core.medicine_data import get_medicines_by_type


def test_get_medicines_by_type_none_returns_empty():
    assert get_medicines_by_type(None) == []


def test_get_medicines_by_type_blank_returns_empty():
    assert get_medicines_by_type("   ") == []
