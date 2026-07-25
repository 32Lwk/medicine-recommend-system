"""Phase 4: meta safety shortpath + concierge execution sync tests。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.safety_gate import run_safety_gate
from src.dialogue.routing.meta_safety_shortpath import is_meta_safety_shortpath_eligible
from src.services.concierge_execution_sync import sync_concierge_execution_metadata


def test_meta_shortpath_eligible_for_doc_changelog_dispatch():
    session = {
        "_intent_router_shadow": {
            "primary_route": "Concierge",
            "sub_route": "doc_changelog",
        }
    }
    triage = {"category": "Other", "concierge_intent": "doc_changelog", "_intent_router_dispatch": True}
    assert is_meta_safety_shortpath_eligible(triage, session) is True


def test_meta_shortpath_not_eligible_for_physical():
    triage = {"category": "Physical", "subcategory": "rule_based_recommend"}
    assert is_meta_safety_shortpath_eligible(triage, {}) is False


@pytest.fixture(autouse=True)
def _enable_shortpath(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


def test_safety_gate_skips_emergency_on_meta_shortpath():
    session = {
        "_intent_router_shadow": {
            "primary_route": "Concierge",
            "sub_route": "app_about",
        }
    }
    triage = {"category": "Other", "concierge_intent": "app_about"}
    with patch("src.handlers.chat.chat_emergency_handler.handle_emergency_if_detected") as mock_em:
        mock_em.return_value = None
        result = run_safety_gate(
            session,
            MagicMock(),
            "sid",
            "あなたについて",
            "あなたについて",
            triage_result=triage,
            recommendation_client=MagicMock(),
            phase="full",
        )
    assert result.blocked is False
    mock_em.assert_not_called()


def test_concierge_execution_sync_updates_diagnosis():
    session = {
        "messages": [
            {
                "type": "bot",
                "diagnosis": {
                    "kind": "concierge_architecture",
                    "feedback_context": {"ai_response": "concierge:architecture"},
                },
            }
        ],
        "_intent_router_shadow": {"sub_route": "app_about"},
    }
    triage = {"category": "Other", "concierge_intent": "architecture"}
    sync_concierge_execution_metadata(
        session,
        sid="sid-1",
        resolved_intent="app_about",
        triage_result=triage,
        user_text="あなたについて詳しく",
    )
    assert triage["concierge_intent"] == "app_about"
    diag = session["messages"][-1]["diagnosis"]
    assert diag["kind"] == "concierge_app_about"
    assert diag["feedback_context"]["concierge_intent"] == "app_about"
