"""medicine_qa_routing — multi-focus / route arbitration テスト。"""
from __future__ import annotations

from src.services.medicine_qa_routing import (
    infer_medicine_qa_focuses,
    is_medicine_information_question,
    needs_medicine_clarification,
    should_use_medicine_qa_unified,
)


def test_mixed_side_effect_and_photo_uses_unified_route():
    msg = "ロキソニンの副作用と写真見せて"
    focuses = infer_medicine_qa_focuses(msg)
    assert "side_effect" in focuses
    assert "product_image" in focuses
    assert should_use_medicine_qa_unified(focuses)
    assert is_medicine_information_question(msg)


def test_pure_side_effect_stays_csv_route():
    msg = "ロキソニンって眠い？"
    focuses = infer_medicine_qa_focuses(msg)
    assert focuses == ["side_effect"]
    assert not should_use_medicine_qa_unified(focuses)


def test_anaphora_needs_clarify_without_history():
    msg = "この薬の用法は？"
    assert needs_medicine_clarification(msg)
    assert not is_medicine_information_question(msg)


def test_ingredient_only_side_effect_question():
    msg = "イブプロフェンの副作用は？"
    focuses = infer_medicine_qa_focuses(msg)
    assert "side_effect" in focuses


def test_comparison_pick_focus():
    msg = "ロキソニンとイブどっちがいい？"
    focuses = infer_medicine_qa_focuses(msg)
    assert "comparison" in focuses


def test_three_product_comparison_stays_neutral():
    from src.services.medicine_qa_routing import is_comparison_pick_question

    msg = "ロキソニンとイブとバファリン、どれがいい？"
    focuses = infer_medicine_qa_focuses(msg)
    assert "comparison" in focuses
    assert is_comparison_pick_question(msg)
    # 3製品以上は pick 対象外（entity 解決は別途だが focus は comparison）
