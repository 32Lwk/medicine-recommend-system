"""メタ／技術質問の sticky 回避・ルーター優先の回帰テスト。"""
from __future__ import annotations

import pytest

from src.agents.concierge_agent import resolve_concierge_intent
from src.dialogue.routing.context_signals import (
    is_doc_changelog_continuation,
    is_explicit_new_meta_topic,
    looks_like_substantive_meta_question,
)
from src.dialogue.routing.unified_router import resolve_unified_route
from src.services.concierge_agent_history import resolve_concierge_follow_up_intent


@pytest.fixture(autouse=True)
def _enable_unified_flags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def _session_after(intent: str, user: str = "最近の更新を教えて") -> dict:
    return {
        "messages": [
            {"type": "user", "content": user},
            {
                "type": "bot",
                "content": "応答",
                "concierge_intent": intent,
                "diagnosis": {"kind": f"concierge_{intent}"},
            },
        ],
        "last_concierge_intent": intent,
    }


def test_aws_gcp_after_changelog_is_new_topic():
    text = "AWSとGCPの違いは？"
    assert is_explicit_new_meta_topic(text, prior_intent="doc_changelog")
    assert resolve_concierge_follow_up_intent(text, "doc_changelog") is None
    decision = resolve_unified_route(
        text, _session_after("doc_changelog"), "sid-aws", triage_result={"category": "Other"}
    )
    assert decision.sub_route == "architecture"


def test_architecture_short_after_app_about():
    text = "アーキテクチャーは？"
    assert looks_like_substantive_meta_question(text) or is_explicit_new_meta_topic(
        text, prior_intent="app_about"
    )
    assert resolve_concierge_follow_up_intent(text, "app_about") is None
    decision = resolve_unified_route(
        text, _session_after("app_about", "システムについて"), "sid-arch", triage_result={"category": "Other"}
    )
    assert decision.sub_route == "architecture"


def test_who_is_answering_after_architecture_is_app_about():
    text = "今回答しているのはだれ？"
    decision = resolve_unified_route(
        text,
        _session_after("architecture", "アーキテクチャは？"),
        "sid-who",
        triage_result={"category": "Other"},
    )
    assert decision.sub_route == "app_about"


def test_changelog_continuation_still_sticky():
    text = "もっと詳しく"
    assert is_doc_changelog_continuation(text)
    assert resolve_concierge_follow_up_intent(text, "doc_changelog") == "doc_changelog"


def test_router_dispatch_beats_sticky_follow_up_without_execution_lock():
    """router_dispatch があれば sticky follow-up より Concierge intent を優先。"""
    session = _session_after("doc_changelog")
    # execution_lock なしでも dispatch を尊重
    triage = {
        "category": "Other",
        "_intent_router_dispatch": True,
        "concierge_intent": "architecture",
    }
    intent = resolve_concierge_intent(
        "AWSとGCPの違いは？",
        session,
        triage_result=triage,
        session_id="sid-dispatch",
        conversation_history=session["messages"],
    )
    assert intent == "architecture"
