"""concierge_context テスト。"""
from __future__ import annotations

from src.dialogue.concierge_context import resolve_off_topic_turns


def test_resolve_off_topic_turns_from_dialogue_state(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session = {
        "dialogue_state": {
            "version": 1,
            "concierge": {"off_topic_turns": 2, "last_intent": "chitchat"},
        },
        "concierge_state": {"off_topic_turns": 0},
    }
    assert resolve_off_topic_turns(session, "line:U1") == 2


def test_resolve_off_topic_turns_legacy_fallback(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    session = {"concierge_state": {"off_topic_turns": 3}}
    assert resolve_off_topic_turns(session, "line:U1") == 3
