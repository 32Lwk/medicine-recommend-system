"""メタ話題の日常表現 — family / sticky / topic break 回帰。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.dialogue.routing.context_signals import (
    is_explicit_new_meta_topic,
    suggest_meta_intent_family,
)
from src.dialogue.routing.unified_router import resolve_unified_route
from src.services.concierge_agent_history import resolve_concierge_follow_up_intent

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "meta_topic_everyday_eval.yaml"


@pytest.fixture(autouse=True)
def _enable_unified_flags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def _cases() -> list[dict]:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8")) or {}
    return list(data.get("cases") or [])


def _session_after(intent: str | None) -> dict:
    if not intent:
        return {"messages": []}
    return {
        "messages": [
            {"type": "user", "content": "prev"},
            {
                "type": "bot",
                "content": "応答",
                "concierge_intent": intent,
                "diagnosis": {"kind": f"concierge_{intent}"},
            },
        ],
        "last_concierge_intent": intent,
    }


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.get("id", "case"))
def test_meta_topic_everyday_case(case: dict):
    query = str(case.get("query") or "")
    prior = case.get("prior_intent")
    if prior is not None:
        prior = str(prior)

    fam = suggest_meta_intent_family(query)
    expect_fam = case.get("expect_family")
    assert fam == expect_fam

    if "expect_topic_break" in case and prior is not None:
        assert is_explicit_new_meta_topic(query, prior_intent=prior) is bool(
            case.get("expect_topic_break")
        )

    sticky = resolve_concierge_follow_up_intent(query, prior)
    if case.get("expect_follow_up_sticky"):
        assert sticky == prior
    else:
        assert sticky is None

    expect_sub = case.get("expect_unified_sub_route")
    if expect_sub:
        decision = resolve_unified_route(
            query,
            _session_after(prior),
            f"meta-edy-{case.get('id')}",
            triage_result={"category": "Other"},
        )
        assert decision.sub_route == expect_sub
