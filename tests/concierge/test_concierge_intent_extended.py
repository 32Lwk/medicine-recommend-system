"""Concierge 意図分類の拡張境界テスト（高速パス）"""
from unittest.mock import MagicMock, patch

import pytest

from src.agents.concierge_agent import resolve_concierge_intent, should_concierge_handle
from src.services.concierge_intent import (
    classify_concierge_intent,
    is_excluded_service_app_about_request,
    probe_meta_concierge_intent,
    probe_service_app_about_request,
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


def test_otc_definition_with_capabilities_intent_routes_to_concierge():
    triage = {
        "category": "Other",
        "confidence": 0.99,
        "concierge_intent": "capabilities",
        "concierge_intent_source": "meta_triage",
    }
    assert should_concierge_handle("OTCってなに？", triage)
    session = {"concierge_state": {}}
    assert (
        resolve_concierge_intent(
            "OTCってなに？",
            session,
            triage_result=triage,
            client=MagicMock(),
        )
        == "capabilities"
    )


def test_otc_definition_is_not_medicine_consultation_block():
    from src.services.concierge_intent import probe_meta_concierge_intent

    assert probe_meta_concierge_intent("OTCってなに？") == "capabilities"


def test_who_answered_routes_to_architecture_probe():
    from src.services.concierge_intent import probe_meta_concierge_intent

    assert probe_meta_concierge_intent("誰が回答したの？") == "architecture"


def test_should_exit_counseling_for_meta_question():
    from src.services.concierge_intent import should_exit_counseling_for_concierge

    assert should_exit_counseling_for_concierge(
        "誰が回答したの？",
        triage_result={"category": "Other", "concierge_intent": "architecture"},
    )
    assert should_exit_counseling_for_concierge(
        "OTCってなに？",
        triage_result={"category": "Other", "concierge_intent": "capabilities"},
    )
    assert should_exit_counseling_for_concierge("薬機法上問題ないの？")
    assert not should_exit_counseling_for_concierge("まだ眠れない")


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
        ("今答えているのは誰？", "architecture"),
        ("プライバシーポリシーは？", "doc_privacy"),
        ("プラポリは？", "doc_privacy"),
        ("薬機法上問題ないの？", "doc_terms"),
        ("利用規約は？", "doc_terms"),
    ],
)
def test_probe_meta_concierge_intent(text, expected):
    assert probe_meta_concierge_intent(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "私の自己紹介するね",
        "僕の自己紹介を聞いて",
        "このポケモンのアプリの紹介して",
        "あのアプリを紹介して",
    ],
)
def test_probe_meta_skips_excluded_app_about(text):
    assert probe_meta_concierge_intent(text) is None
    assert is_excluded_service_app_about_request(text)
    assert not probe_service_app_about_request(text)


@pytest.mark.parametrize(
    "text",
    [
        "自己紹介して",
        "自己紹介してください",
        "あなたについて教えて",
        "このアプリについて",
    ],
)
def test_probe_service_app_about_request_positive(text):
    assert probe_service_app_about_request(text)
    assert not is_excluded_service_app_about_request(text)


def test_probe_skips_medicine_consultation():
    assert probe_meta_concierge_intent("風邪薬を教えて") is None
    assert probe_meta_concierge_intent("頭が痛い") is None


def test_build_ambiguous_meta_clarification():
    from src.services.concierge_intent import build_ambiguous_meta_clarification

    assert build_ambiguous_meta_clarification("技術？") is not None
    assert build_ambiguous_meta_clarification("それについて教えて") is not None
    assert build_ambiguous_meta_clarification("頭が痛い") is None


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
