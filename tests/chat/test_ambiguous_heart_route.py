"""Ambiguous_Heart 確認カード"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_ambiguous_heart_route import (
    is_ambiguous_heart_triage,
    try_ambiguous_heart_clarification,
)


def test_is_ambiguous_heart_triage():
    assert is_ambiguous_heart_triage({"subcategory": "Ambiguous_Heart"})
    assert is_ambiguous_heart_triage({"subcategory": "ambiguous_heart"})
    assert not is_ambiguous_heart_triage({"subcategory": "heart_pain"})


@patch("src.services.sage_bot_response.build_bot_response")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
def test_ambiguous_heart_clarification_once(mock_get, mock_save, mock_build):
    mock_build.return_value = {
        "type": "bot",
        "content": "sage_status",
        "ambiguous_heart_clarification": True,
    }
    session = {"messages": []}
    triage = {"category": "Emotional", "subcategory": "Ambiguous_Heart", "confidence": 0.8}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = try_ambiguous_heart_clarification(
        session,
        client,
        "sid-ah",
        "心が痛い",
        "心が痛い",
        triage,
    )
    assert resp is not None
    assert session.get("ambiguous_heart_clarify_sent") is True
    assert len(session["messages"]) == 1
    sage_diag = mock_build.call_args.kwargs["sage_diagnosis"]
    assert sage_diag["kind"] == "ambiguous_heart_clarification"

    second = try_ambiguous_heart_clarification(
        session,
        client,
        "sid-ah",
        "心が痛い",
        "心が痛い",
        triage,
    )
    assert second is None
