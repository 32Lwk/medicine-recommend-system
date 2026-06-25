"""Concierge 履歴の担当エージェント推定テスト。"""
from __future__ import annotations

from src.services.concierge_agent_history import (
    format_concierge_agent_history_block,
    is_architecture_explanation_question,
    is_multi_agent_concept_question,
    is_who_is_answering_question,
    resolve_bot_responding_agent,
    resolve_last_responding_agent,
)


def test_resolve_concierge_bot_agent():
    msg = {
        "type": "bot",
        "concierge": True,
        "concierge_intent": "architecture",
        "content": "説明",
    }
    assert resolve_bot_responding_agent(msg) == "ConciergeAgent"


def test_history_block_includes_agent_label():
    block = format_concierge_agent_history_block(
        [
            {"type": "user", "content": "仕組みは？"},
            {
                "type": "bot",
                "concierge": True,
                "concierge_intent": "architecture",
                "content": "マルチエージェントです",
            },
            {"type": "user", "content": "今答えているのは誰？"},
        ]
    )
    assert "bot[ConciergeAgent]:" in block
    assert "今答えているのは誰？" in block


def test_who_is_answering_question_detected():
    assert is_who_is_answering_question("今答えているのは誰？")
    assert is_who_is_answering_question("誰が回答したの？")


def test_multi_agent_concept_not_who_question():
    assert is_multi_agent_concept_question("マルチエージェントは何？")
    assert is_architecture_explanation_question("マルチエージェントの構成を教えて")
    assert is_architecture_explanation_question("役割分担を説明して")
    assert not is_architecture_explanation_question("今答えているのは誰？")


def test_resolve_last_responding_agent():
    messages = [
        {"type": "user", "content": "こんにちは"},
        {"type": "bot", "concierge": True, "content": "案内"},
    ]
    assert resolve_last_responding_agent(messages) == "ConciergeAgent"
