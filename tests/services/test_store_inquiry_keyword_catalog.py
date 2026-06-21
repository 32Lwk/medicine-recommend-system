"""StoreInquiryAgent キーワードカタログの読み込みテスト"""
from src.services.store_inquiry_handler import (
    FACILITY_NAMES,
    FACILITY_NAMES_AMBIGUOUS,
    FACILITY_TYPE_KEYWORDS,
)
from src.services.store_inquiry_keyword_catalog import get_store_inquiry_keywords


def test_catalog_loads_facility_labels():
    kw = get_store_inquiry_keywords()
    assert len(kw.facility_names) >= 60
    assert "コンビニ" in kw.facility_names
    assert "大学" in kw.facility_names


def test_education_labels_are_ambiguous_only_in_defer_set():
    assert "大学" in FACILITY_NAMES_AMBIGUOUS
    assert "大学" in FACILITY_NAMES
    assert "大学" not in FACILITY_TYPE_KEYWORDS


def test_subtype_routing_tags_present():
    kw = get_store_inquiry_keywords()
    assert kw.subtype_routing_tags["facilities"] == "store_facilities"
    assert kw.subtype_routing_tags["inventory"] == "store_inventory"


def test_tourism_requires_spatial_or_location_flag():
    kw = get_store_inquiry_keywords()
    assert kw.subtype_require_spatial_or_location.get("tourism") is True


def test_payment_requires_store_scope_flag():
    kw = get_store_inquiry_keywords()
    assert kw.subtype_require_store_scope.get("payment") is True
