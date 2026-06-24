"""挨拶の早期応答ルート（ConciergeAgent 委譲）"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_greeting_route import try_greeting_response
from src.services.chat_response_service import GREETING_INTRO_POOL, build_greeting_response


def _mock_greeting_llm(text: str):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=text))]
    return mock_resp


def _bot_text(bot_msg: dict) -> str:
    diag = bot_msg.get("diagnosis") or {}
    return diag.get("message") or bot_msg.get("content") or ""


_SAGE_SESSION = {"ui_variant": "sage"}


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_returns_short_response(mock_llm):
    mock_llm.return_value = _mock_greeting_llm("こんにちは！市販薬の相談窓口です。")
    session = {"messages": [], "username": "test", "user_attributes": {}, **_SAGE_SESSION}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        resp = try_greeting_response(session, client, "test-sid", "こんにちは")

    assert resp is not None
    body, status = resp
    assert status == 200
    assert body["status"] == "ok"
    assert len(session["messages"]) == 2
    assert session["messages"][0]["type"] == "user"
    assert session["messages"][0]["content"] == "こんにちは"
    assert session["messages"][1]["type"] == "bot"
    assert "こんには" not in _bot_text(session["messages"][1])
    assert session["messages"][1].get("greeting") is True
    assert session["messages"][1].get("concierge") is True


@patch("src.core.llm_client.chat_completion_create")
def test_casual_greeting_yaa(mock_llm):
    mock_llm.return_value = _mock_greeting_llm("やあ！お薬の相談ならどうぞ。")
    session = {"messages": [], "username": "test", "user_attributes": {}, **_SAGE_SESSION}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        resp = try_greeting_response(session, client, "test-sid", "やあ")

    assert resp is not None
    assert session["messages"][-1].get("greeting") is True
    assert "やあ" in _bot_text(session["messages"][-1])


@patch("src.core.llm_client.chat_completion_create")
def test_casual_greeting_mirrors_user_tone(mock_llm):
    mock_llm.return_value = _mock_greeting_llm(
        "あろはー！市販薬の相談窓口です。お困りごとがあればどうぞ。"
    )
    session = {"messages": [], "username": "test", "user_attributes": {}, **_SAGE_SESSION}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        resp = try_greeting_response(
            session,
            client,
            "test-sid",
            "あろはー",
            triage_result={
                "category": "Other",
                "confidence": 0.99,
                "concierge_intent": "greeting",
            },
        )

    assert resp is not None
    assert "あろはー" in _bot_text(session["messages"][-1])


def test_greeting_no_typo_konnichiwa():
    for _ in range(20):
        text = build_greeting_response("こんにちは")
        assert "こんには" not in text
        assert text in GREETING_INTRO_POOL or text.startswith("こんにちは")


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_repeat_gets_new_turn(mock_llm):
    """2回目の挨拶でもユーザー発言と bot 返信が追記される（過去ログは消えない）。"""
    mock_llm.return_value = _mock_greeting_llm("こんにちは！窓口です。")
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "こんにちは。窓口です。", "greeting": True},
        ],
        "user_attributes": {},
    }
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        resp = try_greeting_response(session, client, None, "こんにちは")

    assert resp is not None
    assert len(session["messages"]) == 4
    assert session["messages"][2]["type"] == "user"
    assert session["messages"][3]["type"] == "bot"


def test_greeting_skips_duplicate_post_only():
    """直前が同一ユーザー発言のときだけ抑止（二重 POST）。"""
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "sage_status", "concierge": True, "greeting": True},
        ],
        "user_attributes": {},
    }
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    resp = try_greeting_response(session, client, "test-sid", "こんにちは")

    assert resp is not None
    assert len(session["messages"]) == 2


def test_symptom_not_greeting():
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    resp = try_greeting_response(
        session,
        client,
        None,
        "頭痛がする",
        triage_result={"category": "Physical", "confidence": 0.9},
    )

    assert resp is None
    assert session["messages"] == []
