"""medicine_qa_routing — 文脈・併用・効き目の一般化テスト。"""
from __future__ import annotations

from src.services.medicine_qa_routing import (
    infer_medicine_qa_focuses,
    is_medicine_information_question,
    should_use_medicine_qa_unified,
)


def test_alcohol_interaction_from_context():
    history = [
        {"role": "user", "content": "肩こり"},
        {"role": "assistant", "content": "ロキソニン推奨"},
    ]
    q = "ワイン飲んでるけど平気？"
    focuses = infer_medicine_qa_focuses(
        q,
        conversation_history=history,
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )
    assert "interaction" in focuses
    assert is_medicine_information_question(
        q,
        conversation_history=history,
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )


def test_anaphora_side_effect_without_comparison_from_history():
    history = [
        {"role": "user", "content": "イブとロキソどっち"},
        {"role": "assistant", "content": "ロキソニン推奨"},
        {"role": "user", "content": "じゃあロキソで"},
        {"role": "assistant", "content": "承知"},
    ]
    q = "2つ前に言ったやつ、副作用ヤバい？"
    focuses = infer_medicine_qa_focuses(
        q,
        conversation_history=history,
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )
    assert focuses == ["side_effect"]


def test_efficacy_and_side_effect_uses_unified_route():
    q = "効き目どう？副作用気になる"
    focuses = infer_medicine_qa_focuses(
        q,
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )
    assert "side_effect" in focuses
    assert should_use_medicine_qa_unified(focuses, user_message=q)
    assert is_medicine_information_question(
        q,
        recommended_medicines=[{"product_name": "ロキソニン"}],
    )
