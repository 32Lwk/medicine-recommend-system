"""Concierge 意図分類の拡張境界テスト（高速パス）"""
from unittest.mock import MagicMock, patch

import pytest

from src.agents.concierge_agent import resolve_concierge_intent, should_concierge_handle
from src.services.concierge_intent import (
    classify_concierge_intent,
    probe_meta_concierge_intent,
    resolve_pre_triage_concierge_intent,
    should_reset_off_topic,
)
from src.services.concierge_orchestrator import enrich_other_concierge_intent


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ありがとう", "thanks"),
        ("こんにちは", "greeting"),
        ("やあ", "greeting"),
        ("やっほ", "greeting"),
    ],
)
def test_classify_exact_match_intent_param(text, expected):
    assert classify_concierge_intent(text) == expected


def test_chitchat_is_not_fast_keyword():
    assert classify_concierge_intent("今日はいい天気") is None


@pytest.mark.parametrize(
    "text",
    [
        "マルチエージェントなの？",
        "何ができる？",
        "あなたにできることをまとめて",
        "あなたは誰？",
        "頭が痛い",
        "陸上競技でも使える風邪薬を教えてください。",
    ],
)
def test_meta_and_medical_not_fast_keyword(text):
    assert classify_concierge_intent(text) is None


def test_physical_triage_skips_symptom_concierge():
    assert not should_concierge_handle("頭が痛い", {"category": "Physical", "confidence": 0.95})


def test_greeting_handles_even_when_physical_triage():
    assert should_concierge_handle("やあ", {"category": "Physical", "confidence": 0.5})


def test_other_triage_handles_concierge():
    assert should_concierge_handle("できること", {"category": "Other", "confidence": 0.99})


def test_redirect_after_two_chitchat():
    session = {"concierge_state": {"off_topic_turns": 2}}
    triage = {"concierge_intent": "chitchat"}
    assert (
        resolve_concierge_intent(
            "今日はいい天気ですね", session, triage_result=triage
        )
        == "redirect"
    )


def test_reset_on_medicine_keyword():
    assert should_reset_off_topic("市販薬を教えて")


def test_none_for_empty():
    assert classify_concierge_intent("") is None
    assert classify_concierge_intent("   ") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("あなたについて教えてください", "app_about"),
        ("あんたについて教えて", "app_about"),
        ("自己紹介してください", "app_about"),
        ("何ができる？", "capabilities"),
        ("マルチエージェントなの？", "architecture"),
        ("プライバシーポリシーは？", "doc_privacy"),
    ],
)
def test_probe_meta_concierge_intent(text, expected):
    assert probe_meta_concierge_intent(text) == expected


def test_probe_skips_medicine_consultation():
    assert probe_meta_concierge_intent("風邪薬を教えて") is None
    assert probe_meta_concierge_intent("頭が痛い") is None


def test_resolve_pre_triage_includes_greeting_and_meta():
    assert resolve_pre_triage_concierge_intent("こんにちは") == "greeting"
    assert resolve_pre_triage_concierge_intent("あなたについて") == "app_about"


@patch("src.core.llm_client.chat_completion_create")
def test_orchestrator_meta_app_about_dialect(mock_chat):
    import json
    from unittest.mock import MagicMock

    body = json.dumps({"intent": "app_about", "confidence": 0.95})
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=body))]
    )
    triage = {"category": "Other", "confidence": 0.99, "subcategory": "general_other"}
    enriched = enrich_other_concierge_intent(
        triage,
        "あんたについて教えて",
        MagicMock(),
        conversation_history=[],
    )
    assert enriched["concierge_intent"] == "app_about"
    session = {"concierge_state": {}}
    assert resolve_concierge_intent(
        "あんたについて教えて",
        session,
        triage_result=enriched,
        client=MagicMock(),
    ) == "app_about"
