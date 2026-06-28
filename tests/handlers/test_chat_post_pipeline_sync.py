"""chat_post_pipeline v2 同期フックのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.handlers.chat.chat_post_pipeline import ChatPostContext, sync_routing_context


def test_sync_routing_context_mirrors_dialogue_state(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session = {
        "counseling_mode": {"active": True, "symptom_type": "general_emotional"},
        "agent_handoff": "CounselingManager",
        "messages": [],
    }
    ctx = ChatPostContext(
        session=session,
        client_info=MagicMock(),
        sid="line:U1",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        triage_result={"category": "Emotional", "confidence": 0.9},
        user_message="眠れません",
        sanitized_message="眠れません",
    )
    sync_routing_context(ctx)
    assert session["dialogue_state"]["counseling"]["active"] is True
    assert session["dialogue_state"]["handoff"]["target"] == "CounselingManager"


def test_sync_routing_context_mirrors_concierge_state(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session = {
        "concierge_state": {"last_intent": "architecture", "off_topic_turns": 1},
        "messages": [],
    }
    ctx = ChatPostContext(
        session=session,
        client_info=MagicMock(),
        sid="line:U2",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        triage_result={"category": "Other", "confidence": 0.9},
        user_message="技術面を詳しく",
        sanitized_message="技術面を詳しく",
    )
    sync_routing_context(ctx)
    assert session["dialogue_state"]["concierge"]["last_intent"] == "architecture"
    assert session["dialogue_state"]["concierge"]["off_topic_turns"] == 1
