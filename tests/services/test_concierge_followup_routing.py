"""Phase 3 (p3-concierge MR-4): Concierge フォローアップ文脈維持テスト。"""
from __future__ import annotations

import pytest

from src.dialogue.routing.gate import run_deterministic_gate
from src.services.concierge_agent_history import (
    infer_enhanced_concierge_follow_up_intent,
    resolve_concierge_follow_up_intent,
)


@pytest.fixture
def followup_flag_on(monkeypatch):
    monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "true")


@pytest.fixture
def followup_flag_off(monkeypatch):
    monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "false")


@pytest.mark.parametrize(
    "setup_intent,input_text,expected",
    [
        ("redirect", "具体例を教えて", "redirect"),
        ("architecture", "SSEについて", "architecture"),
        ("architecture", "Cloud Runは？", "architecture"),
        ("architecture", "rule_basedの詳細", "architecture"),
        ("capabilities", "英語でも使えますか", "capabilities"),
        ("architecture", "具体例を教えて", "architecture"),
    ],
)
def test_enhanced_follow_up_flag_on(
    followup_flag_on, setup_intent, input_text, expected
):
    assert (
        infer_enhanced_concierge_follow_up_intent(input_text, setup_intent)
        == expected
    )


@pytest.mark.parametrize(
    "setup_intent,input_text",
    [
        ("redirect", "具体例を教えて"),
        ("architecture", "SSEについて"),
        ("capabilities", "英語でも使えますか"),
    ],
)
def test_enhanced_follow_up_flag_off_via_resolver(
    followup_flag_off, setup_intent, input_text
):
    assert resolve_concierge_follow_up_intent(input_text, setup_intent) is None


def test_resolve_includes_base_follow_up_without_flag(followup_flag_off):
    assert resolve_concierge_follow_up_intent("もっと詳しく", "architecture") == "architecture"


def test_gate_redirect_follow_up(followup_flag_on):
    session = {
        "messages": [
            {"type": "user", "content": "プリンシプルオブプログラミングとは？"},
            {
                "type": "bot",
                "content": "市販薬のご相談へ",
                "concierge_intent": "redirect",
            },
        ],
        "concierge_state": {"last_intent": "redirect"},
    }
    d = run_deterministic_gate("具体例を教えて", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "redirect"
    assert d.source == "concierge_follow_up"


def test_gate_architecture_topic_follow_up(followup_flag_on):
    session = {
        "messages": [
            {"type": "user", "content": "APIの仕組みを教えて"},
            {
                "type": "bot",
                "content": "API は ...",
                "concierge_intent": "architecture",
            },
        ],
        "concierge_state": {"last_intent": "architecture"},
    }
    d = run_deterministic_gate("SSEについて", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "architecture"


def test_gate_capabilities_language_follow_up(followup_flag_on):
    session = {
        "messages": [
            {"type": "user", "content": "対応言語は？"},
            {
                "type": "bot",
                "content": "日本語など",
                "concierge_intent": "capabilities",
            },
        ],
        "concierge_state": {"last_intent": "capabilities"},
    }
    d = run_deterministic_gate("英語でも使えますか", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "capabilities"


def test_gate_follow_up_beats_physical_symptom_false_positive(followup_flag_on):
    """フォローアップ検出は gate 先頭で症状ルートより優先される。"""
    session = {
        "messages": [
            {"type": "user", "content": "インフラ構成を教えて"},
            {
                "type": "bot",
                "content": "Cloud Run 等",
                "concierge_intent": "architecture",
            },
        ],
        "concierge_state": {"last_intent": "architecture"},
    }
    d = run_deterministic_gate("Cloud Runは？", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.primary_route != "Physical"


def test_enhanced_skips_explicit_symptom(followup_flag_on):
    assert (
        infer_enhanced_concierge_follow_up_intent("頭痛の詳細", "architecture")
        is None
    )
