"""Emergency 経路マトリクス（計画どおり）"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.emergency_classifier import classify_emergency, is_emergency_candidate


@pytest.mark.parametrize(
    "text,triage,mod,expected_subtype",
    [
        ("胸が痛い", {"category": "Emergency", "confidence": 0.9}, None, "medical_self"),
        ("店内で人が倒れている", {"category": "Emergency"}, None, "store_incident"),
        ("もう消えたい", {"category": "Emotional"}, "crisis", "crisis_language"),
    ],
)
def test_classify_emergency_matrix(text, triage, mod, expected_subtype):
    c = classify_emergency(text, triage_result=triage, moderation_label=mod)
    assert c.subtype == expected_subtype


def test_is_emergency_candidate_negative():
    assert not is_emergency_candidate("頭痛", triage_result={"category": "Physical", "confidence": 0.9})


@patch("src.handlers.chat.emergency_dispatch._finalize_emergency_response")
@patch("src.agents.emergency_classifier.is_emergency_candidate", return_value=True)
def test_dispatch_medical_not_none(mock_cand, mock_fin):
    from src.handlers.chat.emergency_dispatch import dispatch_emergency

    mock_fin.return_value = ({"status": "ok", "emergency_detected": True}, 200)
    session = {"messages": [], "language": "ja"}
    resp = dispatch_emergency(
        session,
        MagicMock(),
        "sid-m",
        "胸が痛い",
        MagicMock(),
        {"category": "Emergency"},
    )
    assert resp is not None


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch("src.handlers.chat_orchestrator.ChatOrchestrator")
def test_orchestrator_emergency_returns_response(mock_orch, _on):
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import try_orchestrator_route
    from src.utils.chat_http_context import ChatClientInfo

    mock_orch.return_value.route.return_value.resolved = True
    mock_orch.return_value.route.return_value.response = ({"status": "ok"}, 200)
    ctx = ChatPostContext(
        session={"messages": [], "user_attributes": {}},
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="t"),
        sid="s",
        monitor=MagicMock(),
        user_agent="t",
        client_ip="127.0.0.1",
        user_message="胸が痛い",
        sanitized_message="胸が痛い",
        processed_message="胸が痛い",
        triage_result={"category": "Emergency", "confidence": 0.95},
        trace_id="t",
        recommendation_client=MagicMock(),
    )
    assert try_orchestrator_route(ctx, MagicMock()) is not None
