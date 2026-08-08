"""medicine_qa_routing — 副作用 Q&A と一般医薬品 Q&A の切り分けテスト。"""
from __future__ import annotations

from src.services.medicine_qa_routing import (
    _has_comparison_intent,
    infer_medicine_qa_focuses,
    is_medicine_information_question,
    is_symptom_pivot_followup,
    is_symptom_recommendation_followup,
    is_strict_medicine_side_effect_question,
    is_travel_import_context,
    should_prioritize_physical_for_symptom,
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


def test_travel_import_not_home_inventory():
    assert is_travel_import_context("空港で止められる可能性はあるのかな？")
    assert is_travel_import_context("海外に持っていく場合の注意点")
    assert not is_travel_import_context("うちにもロキソニンあるわ")


def test_symptom_followup_blocks_comparison_with_recs():
    history = [{"type": "user", "content": "頭痛と吐き気がする"}]
    recs = [{"product_name": "イブ"}, {"product_name": "バファリン"}]
    msg = "市販薬で何かある？"
    assert is_symptom_recommendation_followup(msg, conversation_history=history, recommended_medicines=recs)
    assert not _has_comparison_intent(
        msg,
        conversation_history=history,
        recommended_medicines=recs,
    )


def test_travel_followup_gets_doping_focus():
    history = [{"type": "user", "content": "タイ旅行にロキソニン持っていきたい"}]
    focuses = infer_medicine_qa_focuses(
        "空港で引っかかったりしない？",
        conversation_history=history,
        use_llm_enrichment=False,
    )
    assert "doping" in focuses


def test_symptom_pivot_blocks_comparison():
    history = [
        {"type": "user", "content": "鼻水が止まらない"},
        {"type": "bot", "content": "スカイブブロンをご案内"},
    ]
    recs = [{"product_name": "スカイブブロンHI"}]
    msg = "咳も出てきて、咳に効く薬も教えて"
    assert is_symptom_pivot_followup(msg, conversation_history=history, recommended_medicines=recs)
    assert should_prioritize_physical_for_symptom(
        msg, conversation_history=history, recommended_medicines=recs
    )
    assert not _has_comparison_intent(msg, conversation_history=history, recommended_medicines=recs)


def test_anaphora_efficacy_not_comparison():
    history = [{"type": "user", "content": "肩こり限界"}]
    recs = [{"product_name": "バンテリンコーワゲルLT"}]
    msg = "それ、1番目のやつってどんな効果があるの？"
    assert not _has_comparison_intent(msg, conversation_history=history, recommended_medicines=recs)
    focuses = infer_medicine_qa_focuses(
        msg, conversation_history=history, recommended_medicines=recs, use_llm_enrichment=False
    )
    assert "comparison" not in focuses


def test_cold_chip_skipped_when_asking_medicine():
    from src.core.recommendation.cold_symptom_expansion import should_prompt_cold_symptoms

    assert not should_prompt_cold_symptoms("風邪っぽいんやけど、薬何がええ？")

