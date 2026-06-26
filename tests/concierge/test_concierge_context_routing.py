"""Concierge 文脈ルーティング（フォローアップ・structural guard・永続化）"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.concierge_agent_history import (
    infer_lost_context_follow_up_intent,
    infer_prior_meta_follow_up_intent,
    is_meta_follow_up_utterance,
    resolve_prior_meta_intent,
    should_block_structural_greeting,
)
from src.services.concierge_intent import infer_structural_concierge_intent
from src.services.concierge_orchestrator import enrich_other_concierge_intent
from src.services.meta_triage import should_skip_meta_triage_llm

_TRIAGE = {
    "category": "Other",
    "confidence": 0.9,
    "subcategory": "general_other",
}


def test_is_meta_follow_up_utterance():
    assert is_meta_follow_up_utterance("技術面を詳しく")
    assert is_meta_follow_up_utterance("もっと教えて")
    assert not is_meta_follow_up_utterance("うい")


def test_infer_lost_context_architecture():
    assert infer_lost_context_follow_up_intent("技術面を詳しく") == "architecture"
    assert infer_lost_context_follow_up_intent("うい") is None


def test_doc_privacy_follow_up():
    assert infer_prior_meta_follow_up_intent("もっと詳しく", "doc_privacy") == "doc_privacy"


def test_session_ops_follow_up_requires_session_bot():
    status_bot = {
        "type": "bot",
        "session_agent": True,
        "session_agent_kind": "status",
        "concierge_intent": "session_ops",
    }
    assert (
        infer_prior_meta_follow_up_intent(
            "詳しく", "session_ops", last_bot=status_bot
        )
        == "session_ops"
    )
    assert infer_prior_meta_follow_up_intent("詳しく", "session_ops", last_bot=None) is None


def test_resolve_prior_meta_intent_prefers_session_state():
    session = {"concierge_state": {"last_intent": "architecture", "off_topic_turns": 0}}
    history = [{"type": "bot", "concierge_intent": "capabilities"}]
    assert resolve_prior_meta_intent(session=session, conversation_history=history) == "architecture"


def test_should_block_structural_greeting():
    assert should_block_structural_greeting("技術面を詳しく")
    assert should_block_structural_greeting("うい", prior_intent="architecture")
    assert not should_block_structural_greeting("うい")


def test_structural_greeting_blocked_for_follow_up():
    assert infer_structural_concierge_intent("技術面を詳しく") is None
    assert infer_structural_concierge_intent("うい") == "greeting"


def test_should_not_skip_meta_for_follow_up():
    assert (
        should_skip_meta_triage_llm(_TRIAGE, "技術面を詳しく", store_probable=False)
        is False
    )


def test_should_not_skip_meta_when_prior_architecture():
    assert (
        should_skip_meta_triage_llm(
            _TRIAGE,
            "うい",
            store_probable=False,
            prior_meta_intent="architecture",
        )
        is False
    )


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_lost_context_follow_up_without_history(mock_meta):
    mock_meta.return_value = None
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE),
        "技術面を詳しく",
        MagicMock(),
        conversation_history=None,
        session=None,
    )
    assert enriched.get("concierge_intent") == "architecture"
    assert enriched.get("concierge_intent_source") == "lost_context_follow_up"
    mock_meta.assert_not_called()


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_follow_up_from_concierge_state(mock_meta):
    mock_meta.return_value = None
    session = {"concierge_state": {"last_intent": "architecture", "off_topic_turns": 0}}
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE),
        "技術面を詳しく",
        MagicMock(),
        conversation_history=[],
        session=session,
    )
    assert enriched.get("concierge_intent") == "architecture"
    assert enriched.get("concierge_intent_source") == "prior_intent_follow_up"
    mock_meta.assert_not_called()


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_doc_follow_up(mock_meta):
    mock_meta.return_value = None
    history = [
        {"type": "user", "content": "プライバシーポリシーは？"},
        {"type": "bot", "concierge": True, "concierge_intent": "doc_privacy", "content": "..."},
    ]
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE),
        "もっと詳しく",
        MagicMock(),
        conversation_history=history,
    )
    assert enriched.get("concierge_intent") == "doc_privacy"
    assert enriched.get("concierge_intent_source") == "prior_intent_follow_up"


@pytest.mark.parametrize(
    "text,expected_source",
    [
        ("うい", "exact_match_gate"),
        ("konn", "structural_greeting"),
    ],
)
@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_true_short_greeting_regression(mock_meta, text: str, expected_source: str):
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE),
        text,
        MagicMock(),
    )
    mock_meta.assert_not_called()
    assert enriched.get("concierge_intent") == "greeting"
    assert enriched.get("concierge_intent_source") == expected_source
