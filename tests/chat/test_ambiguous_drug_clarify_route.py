"""品目未特定 Clarify ルート"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_ambiguous_drug_clarify_route import (
    ambiguous_drug_clarify_message,
    try_ambiguous_drug_clarification,
)
from src.services.e2e_turn_eval import _is_clarify_response


def test_ambiguous_drug_clarify_message_interaction():
    msg = ambiguous_drug_clarify_message("他の薬と一緒に飲んでも大丈夫？")
    assert "飲み合わせ" in msg
    assert _is_clarify_response(msg)


def test_ambiguous_drug_clarify_message_generic():
    msg = ambiguous_drug_clarify_message("副作用は？")
    assert "どのお薬" in msg
    assert _is_clarify_response(msg)


@patch("src.services.sage_bot_response.build_bot_response")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
def test_try_ambiguous_drug_clarification(mock_get, mock_save, mock_build):
    mock_build.return_value = {"type": "bot", "content": "sage_status"}
    session = {"messages": []}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = try_ambiguous_drug_clarification(
        session,
        client,
        "sid-cl",
        "他の薬と一緒に飲んでも大丈夫？",
        "他の薬と一緒に飲んでも大丈夫？",
        route_source="ambiguous_drug_clarify",
    )
    assert resp is not None
    assert len(session["messages"]) == 1
    sage_diag = mock_build.call_args.kwargs["sage_diagnosis"]
    assert sage_diag["kind"] == "concierge_clarify"


def test_try_ambiguous_drug_clarification_skips_other_source():
    session = {"messages": []}
    client = MagicMock()
    resp = try_ambiguous_drug_clarification(
        session,
        client,
        "sid-x",
        "こんにちは",
        "こんにちは",
        route_source="general_chitchat_no_product",
    )
    assert resp is None
