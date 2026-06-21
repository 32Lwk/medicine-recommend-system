"""計画の受け入れ基準・回帰テスト"""
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import should_concierge_handle
from src.handlers.chat.chat_concierge_route import try_concierge_response
from src.handlers.chat.chat_other_counseling_route import run_other_unknown_counseling
from src.services.concierge_intent import classify_concierge_intent


def _bot_message_text(bot_msg: dict) -> str:
    diag = bot_msg.get("diagnosis") or {}
    return diag.get("message") or bot_msg.get("content") or ""


@patch("src.core.llm_client.chat_completion_create")
def test_acceptance_capabilities_card(mock_llm):
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "capabilities", "confidence": 0.95}'))]
    )
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    try_concierge_response(
        session, client, None,
        "あなたにできることをまとめて", "あなたにできることをまとめて",
        {"category": "Other", "confidence": 0.99}, MagicMock(),
    )
    bot = session["messages"][-1]
    assert bot["concierge_intent"] == "capabilities"
    assert "chat-status-card" in bot["content"]
    assert "処方" in bot["content"] or "OTC" in bot["content"] or "一般用" in bot["content"]


@patch("src.core.llm_client.chat_completion_create")
def test_acceptance_architecture_no_denial(mock_llm):
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "architecture", "confidence": 0.9}'))]
    )
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    try_concierge_response(
        session, client, None,
        "マルチエージェントなの？", "マルチエージェントなの？",
        {"category": "Other", "confidence": 0.99}, MagicMock(),
    )
    assert "案内できません" not in session["messages"][-1]["content"]
    assert "TriageAgent" in session["messages"][-1]["content"]


@patch("src.handlers.chat.chat_concierge_route.save_session_to_db")
@patch("src.agents.concierge_agent.concierge_chat")
def test_acceptance_greeting_uses_llm_by_default(mock_chat, _save):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content="はおー！OTC相談窓口です。お困りごとがあればどうぞ。"))
    ]
    mock_chat.return_value = mock_resp
    session = {"messages": [], "user_attributes": {}, "ui_variant": "sage"}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    try_concierge_response(
        session, client, "test-sid",
        "はおー", "はおー",
        {
            "category": "Other",
            "confidence": 0.99,
            "concierge_intent": "greeting",
        },
        MagicMock(),
    )
    mock_chat.assert_called_once()
    assert session["messages"][-1].get("greeting") is True


@patch("src.handlers.chat.chat_concierge_route.save_session_to_db")
@patch("src.agents.concierge_agent.concierge_chat")
def test_acceptance_greeting_falls_back_to_template_on_llm_failure(mock_chat, _save):
    mock_chat.side_effect = RuntimeError("llm unavailable")
    session = {"messages": [], "user_attributes": {}, "ui_variant": "sage"}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    try_concierge_response(
        session, client, "test-sid",
        "はおー", "はおー",
        {
            "category": "Other",
            "confidence": 0.99,
            "concierge_intent": "greeting",
        },
        MagicMock(),
    )
    mock_chat.assert_called_once()
    assert session["messages"][-1].get("greeting") is True
    assert session["messages"][-1]["content"]


@patch("src.core.llm_client.chat_completion_create")
def test_acceptance_chitchat_redirect_third_turn(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "chitchat", "confidence": 0.9}'))]
    )
    session = {"messages": [], "user_attributes": {}, "concierge_state": {"off_topic_turns": 2}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        try_concierge_response(
            session, client, None,
            "今日はいい天気", "今日はいい天気",
            {"category": "Other", "confidence": 0.99}, MagicMock(),
        )
    assert session["messages"][-1]["concierge_intent"] == "redirect"


def test_acceptance_physical_skips_concierge():
    assert classify_concierge_intent("頭が痛い") is None
    assert not should_concierge_handle("頭が痛い", {"category": "Physical", "confidence": 0.9})


def test_regression_other_counseling_skips_meta():
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    result = run_other_unknown_counseling(
        session, client, None,
        "できること", "できること", "できること", "できること",
        {"category": "Other", "confidence": 0.99}, MagicMock(),
    )
    assert result is None
