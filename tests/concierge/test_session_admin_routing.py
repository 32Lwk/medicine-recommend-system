"""session_admin / session_ops / 範囲外 redirect のルーティング補助テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.concierge_agent_history import (
    infer_prior_meta_follow_up_intent,
    resolve_last_concierge_intent,
)
from src.services.concierge_intent import probe_meta_concierge_intent
from src.services.concierge_orchestrator import enrich_other_concierge_intent
from src.services.meta_triage import _VALID_INTENTS


def test_meta_triage_valid_intents_include_session_ops():
    assert "session_ops" in _VALID_INTENTS


def test_programming_question_probe_redirect():
    assert probe_meta_concierge_intent("プリンシプルオブプログラミングとは？") == "redirect"


def test_architecture_follow_up_after_tech_stack():
    history = [
        {"type": "user", "content": "技術スタックは？"},
        {
            "type": "bot",
            "concierge": True,
            "concierge_intent": "architecture",
            "content": "仕組み・技術の説明",
        },
    ]
    assert resolve_last_concierge_intent(history) == "architecture"
    assert infer_prior_meta_follow_up_intent("技術面を詳しく", "architecture") == "architecture"

    enriched = enrich_other_concierge_intent(
        {"category": "Other", "confidence": 0.9},
        "技術面を詳しく",
        None,
        conversation_history=history,
    )
    assert enriched.get("concierge_intent") == "architecture"
    assert enriched.get("concierge_intent_source") == "prior_intent_follow_up"


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_skips_meta_for_triage_session_admin(mock_meta):
    triage = {
        "category": "Other",
        "confidence": 0.95,
        "subcategory": "session_admin",
    }
    enriched = enrich_other_concierge_intent(
        triage,
        "状態は？",
        MagicMock(),
    )
    mock_meta.assert_not_called()
    assert enriched.get("concierge_intent") == "session_ops"
    assert enriched.get("concierge_intent_source") == "triage_session_admin"
    assert enriched.get("session_intent") == "status"
