"""店舗 diagnosis kind の解決テスト。"""
from __future__ import annotations

from src.services.status_diagnosis_builder import resolve_store_diagnosis_kind


def test_resolve_store_locator_for_external_chain() -> None:
    kind = resolve_store_diagnosis_kind(
        {"inquiry_type": "store_inquiry"},
        user_text="マツキヨは近くにありますか",
    )
    assert kind == "store_locator"


def test_resolve_store_locator_for_pharmacy_nearby() -> None:
    kind = resolve_store_diagnosis_kind(
        {"inquiry_type": "store_inquiry"},
        user_text="近くの薬局を教えて",
    )
    assert kind == "store_locator"


def test_resolve_store_facilities_for_toilet() -> None:
    kind = resolve_store_diagnosis_kind(
        {"inquiry_type": "store_inquiry"},
        user_text="トイレはどこですか",
    )
    assert kind == "store_facilities"
