"""reco_followup_signals の単体テスト。"""
from __future__ import annotations

from src.services.reco_followup_signals import (
    is_bot_echo_symptom_interview,
    is_travel_thread_followup,
    is_wellness_alternative_topic,
    message_warrants_reco_rescore,
)


def test_symptom_addition_warrants_rescore() -> None:
    history = [
        {"type": "user", "content": "風邪っぽい"},
        {
            "type": "bot",
            "diagnosis": {
                "recommended_medicines": [{"product_name": "イブ"}],
                "symptoms": ["疲労感"],
            },
        },
    ]
    assert message_warrants_reco_rescore(
        "のども痛いわ。熱はあんまりない",
        conversation_history=history,
        recommended_medicines=[{"product_name": "イブ"}],
    )


def test_bot_echo_symptom_interview_not_sports() -> None:
    msg = "具体的にどんな症状があるか教えてくれる？"
    assert is_bot_echo_symptom_interview(msg)
    assert not is_bot_echo_symptom_interview("明日水泳大会なので競技前に使える薬は？")


def test_travel_thread_followup_from_history() -> None:
    history = [
        {"type": "user", "content": "タイ旅行にロキソニン持っていきたい"},
        {"type": "bot", "content": "持ち込み注意"},
    ]
    assert is_travel_thread_followup(
        "他に気をつけるべきことがあれば教えてほしい",
        conversation_history=history,
    )


def test_wellness_alternative_topic() -> None:
    assert is_wellness_alternative_topic("食物繊維のサプリメントはどう？")


def test_pivot_yappa_warrants_rescore() -> None:
    history = [{"type": "user", "content": "鼻水"}]
    recs = [{"product_name": "スカイブ"}]
    assert message_warrants_reco_rescore(
        "いや、やっぱ咳の方がキツい",
        conversation_history=history,
        recommended_medicines=recs,
    )


def test_travel_thread_followup_quantity_question() -> None:
    history = [
        {"type": "user", "content": "タイ旅行にロキソニン持っていきたい"},
        {"type": "bot", "content": "持ち込み注意"},
    ]
    assert is_travel_thread_followup(
        "持ち込む量はどれくらいがいい？",
        conversation_history=history,
    )

    from src.core.medicine.medicine_response_builder import _try_fast_travel_import_qa_response

    resp = _try_fast_travel_import_qa_response(
        "タイ旅行にロキソニン持っていきたい",
        None,
    )
    assert resp is not None
    assert "タイ" in resp["answer"]
    assert "申し訳" not in resp["answer"]
