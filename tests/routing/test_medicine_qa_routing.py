"""medicine_qa_routing — 副作用 Q&A と一般医薬品 Q&A の切り分けテスト。"""
from __future__ import annotations

from src.services.medicine_qa_routing import (
    is_medicine_information_question,
    is_strict_medicine_side_effect_question,
)
from src.services.medicine_side_effect_routing import is_medicine_side_effect_route


def test_comparison_question_is_medicine_information_not_side_effect():
    msg = "ロキソニンとイブの違いって何？"
    assert is_medicine_information_question(msg)
    assert not is_strict_medicine_side_effect_question(msg)
    assert not is_medicine_side_effect_route(msg)


def test_loxoprofen_drowsiness_remains_side_effect_route():
    msg = "ロキソニンって眠い？"
    assert is_strict_medicine_side_effect_question(msg)
    assert is_medicine_side_effect_route(msg)
    assert not is_medicine_information_question(msg)


def test_which_is_better_is_medicine_information():
    msg = "ロキソニンとイブどっちがいい？"
    assert is_medicine_information_question(msg)
    assert not is_strict_medicine_side_effect_question(msg)


def test_side_effect_keyword_stays_side_effect_route():
    msg = "イブの副作用は？"
    assert is_strict_medicine_side_effect_question(msg)
    assert not is_medicine_information_question(msg)
