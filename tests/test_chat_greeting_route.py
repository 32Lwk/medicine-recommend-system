"""挨拶の早期応答ルート"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_greeting_route import try_greeting_response


def test_greeting_returns_short_response():
    session = {"messages": [], "username": "test"}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    with patch("src.handlers.chat.chat_greeting_route.save_session_to_db"):
        resp = try_greeting_response(session, client, None, "こんにちは")

    assert resp is not None
    body, status = resp
    assert status == 200
    assert body["status"] == "ok"
    assert len(session["messages"]) == 2
    assert session["messages"][0]["type"] == "user"
    assert session["messages"][0]["content"] == "こんにちは"
    assert session["messages"][1]["type"] == "bot"
    assert "症状" in session["messages"][1]["content"]
    assert session["messages"][1].get("greeting") is True


def test_greeting_skips_duplicate_reply():
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "こんにちは！", "greeting": True},
        ]
    }
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    resp = try_greeting_response(session, client, None, "こんにちは")

    assert resp is not None
    assert len(session["messages"]) == 2


def test_symptom_not_greeting():
    session = {"messages": []}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    resp = try_greeting_response(session, client, None, "頭痛がする")

    assert resp is None
    assert session["messages"] == []
