"""Concierge 意図分類のテスト"""
from src.agents.concierge_agent import should_concierge_handle
from src.services.concierge_intent import classify_concierge_intent, should_reset_off_topic


def test_greeting_exact_intent():
    assert classify_concierge_intent("こんにちは") == "greeting"


def test_thanks_exact_intent():
    assert classify_concierge_intent("ありがとう") == "thanks"


def test_medicine_question_not_fast_concierge():
    assert classify_concierge_intent("陸上競技でも使える風邪薬を教えてください。") is None
    assert not should_concierge_handle(
        "陸上競技でも使える風邪薬を教えてください。",
        {"category": "Ask", "confidence": 0.98},
    )


def test_capabilities_not_keyword_match():
    assert classify_concierge_intent("あなたにできることをまとめて") is None


def test_architecture_not_keyword_match():
    assert classify_concierge_intent("マルチエージェントなの？") is None


def test_other_triage_handles_meta_via_concierge():
    assert should_concierge_handle(
        "できること", {"category": "Other", "confidence": 0.99}
    )


def test_physical_triage_skips_concierge():
    assert not should_concierge_handle("頭が痛い", {"category": "Physical", "confidence": 0.9})


def test_reset_off_topic_on_symptom():
    assert should_reset_off_topic("頭が痛いです")
    assert should_reset_off_topic("市販薬を教えて")
