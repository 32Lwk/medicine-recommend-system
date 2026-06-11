"""processing_user_labels: ユーザー向け進捗文言カタログ"""
from __future__ import annotations

from src.services.processing_user_labels import all_user_label_count, get_user_label


def test_user_label_catalog_at_least_fifty():
    assert all_user_label_count() >= 50


def test_detail_label_medicine_qa():
    label = get_user_label("ask_qa", "medicine_qa", "s1", detail_code="interaction_check")
    assert "飲み合わせ" in label
    assert "Agent" not in label
    assert "MedicineQA" not in label


def test_scoring_detail_physical():
    label = get_user_label("physical", "medicine_select", "s2", detail_code="scoring")
    assert "適合" in label or "評価" in label


def test_pick_label_deterministic_per_session():
    a = get_user_label("ask_qa", "triage", "sess-x")
    b = get_user_label("ask_qa", "triage", "sess-x")
    c = get_user_label("ask_qa", "triage", "sess-y")
    assert a == b
    assert isinstance(c, str)
