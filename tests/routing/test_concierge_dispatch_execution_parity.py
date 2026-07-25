"""Concierge dispatch / execution parity regression tests."""
from __future__ import annotations

import pytest

from src.agents.concierge_agent import resolve_concierge_intent
from src.dialogue.routing.unified_router import resolve_unified_route
from src.services.concierge_agent_history import resolve_concierge_follow_up_intent


def _session_after_changelog() -> dict:
    return {
        "messages": [
            {"type": "user", "content": "最近の更新を教えて"},
            {
                "type": "bot",
                "content": "更新履歴です",
                "concierge_intent": "doc_changelog",
                "diagnosis": {"kind": "concierge_doc_changelog"},
            },
        ],
        "last_concierge_intent": "doc_changelog",
    }


@pytest.fixture(autouse=True)
def _enable_unified_flags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def test_changelog_then_app_about_not_doc_changelog_followup():
    session = _session_after_changelog()
    text = "あなたについて詳しく"
    follow = resolve_concierge_follow_up_intent(text, "doc_changelog")
    assert follow is None

    decision = resolve_unified_route(text, session, "sid-1", triage_result={"category": "Other"})
    assert decision.primary_route == "Concierge"
    assert decision.sub_route == "app_about"
    assert decision.execution_lock is True


def test_changelog_then_architecture_not_doc_changelog():
    session = _session_after_changelog()
    text = "AWSとGCPの違いは？"
    follow = resolve_concierge_follow_up_intent(text, "doc_changelog")
    assert follow is None

    decision = resolve_unified_route(text, session, "sid-2", triage_result={"category": "Other"})
    assert decision.sub_route == "architecture"


def test_changelog_continuation_stays_doc_changelog():
    session = _session_after_changelog()
    text = "もっと詳しく"
    follow = resolve_concierge_follow_up_intent(text, "doc_changelog")
    assert follow == "doc_changelog"

    decision = resolve_unified_route(text, session, "sid-3", triage_result={"category": "Other"})
    assert decision.sub_route == "doc_changelog"


def test_execution_lock_skips_concierge_follow_up_override():
    session = _session_after_changelog()
    session["_routing_execution_lock"] = True
    triage = {
        "category": "Other",
        "_intent_router_dispatch": True,
        "concierge_intent": "app_about",
    }
    intent = resolve_concierge_intent(
        "あなたについて詳しく",
        session,
        triage_result=triage,
        session_id="sid-4",
        conversation_history=session["messages"],
    )
    assert intent == "app_about"
