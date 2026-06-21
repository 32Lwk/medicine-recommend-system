"""意味不明な短い入力向けステータスカード返却"""
from datetime import datetime
from unittest.mock import MagicMock

from src.handlers.chat.chat_symptom_route import try_unrecognized_symptom_response
from src.utils.chat_http_context import ChatClientInfo


def test_try_unrecognized_symptom_response_returns_caution_card():
    session = {"messages": [], "user_attributes": {}, "username": "tester"}
    client_info = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    resp = try_unrecognized_symptom_response(
        session,
        client_info,
        "sid-unrecognized",
        "g",
        "g",
    )
    assert resp is not None
    assert resp[0]["status"] == "ok"
    bot = session["messages"][-1]
    assert bot["type"] == "bot"
    assert bot["diagnosis"]["title"] == "症状から医薬品を選べませんでした"
    assert bot["diagnosis"]["variant"] == "caution"
    assert "chat-status-card--caution" in bot["content"] or bot["content"] == "sage_status"


def test_try_unrecognized_symptom_response_skips_valid_symptom():
    session = {"messages": [], "user_attributes": {}}
    client_info = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    resp = try_unrecognized_symptom_response(
        session,
        client_info,
        None,
        "頭が痛い",
        "頭が痛い",
    )
    assert resp is None
    assert session["messages"] == []
