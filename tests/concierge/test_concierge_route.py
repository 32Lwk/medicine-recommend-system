"""Concierge ルート統合テスト"""

from unittest.mock import MagicMock, patch



from src.handlers.chat.chat_concierge_route import (
    try_concierge_response,
)





@patch("src.core.llm_client.chat_completion_create")

def test_capabilities_returns_status_card(mock_llm):

    mock_llm.return_value = MagicMock(

        choices=[MagicMock(message=MagicMock(content='{"intent": "capabilities", "confidence": 0.95}'))]

    )

    session = {"messages": [], "user_attributes": {}}

    client = MagicMock()

    client.client_ip = "127.0.0.1"

    client.user_agent = "test"



    resp = try_concierge_response(

        session,

        client,

        None,

        "あなたにできることをまとめて",

        "あなたにできることをまとめて",

        {"category": "Other", "confidence": 0.99},

        MagicMock(),

    )

    assert resp is not None

    bots = [m for m in session["messages"] if m.get("type") == "bot"]

    assert len(bots) == 1

    assert bots[0].get("concierge_intent") == "capabilities"

    assert "chat-status-card" in bots[0]["content"]





@patch("src.core.llm_client.chat_completion_create")

def test_architecture_no_internal_denial(mock_llm):

    mock_llm.return_value = MagicMock(

        choices=[MagicMock(message=MagicMock(content='{"intent": "architecture", "confidence": 0.9}'))]

    )

    session = {"messages": [], "user_attributes": {}}

    client = MagicMock()

    client.client_ip = "127.0.0.1"

    client.user_agent = "test"



    try_concierge_response(

        session,

        client,

        None,

        "マルチエージェントなの？",

        "マルチエージェントなの？",

        {"category": "Other", "confidence": 0.99},

        MagicMock(),

    )

    content = session["messages"][-1]["content"]

    assert "TriageAgent" in content

    assert "案内できません" not in content





@patch("src.core.llm_client.chat_completion_create")
def test_app_about_via_meta_triage(mock_llm):
    """自己紹介・あなたについてはオーケストレーター meta_triage で app_about カードを返す。"""
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "app_about", "confidence": 0.95}'))]
    )
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = try_concierge_response(
        session,
        client,
        None,
        "あなたについて教えてください。",
        "あなたについて教えてください。",
        {"category": "Other", "confidence": 0.99},
        MagicMock(),
    )
    assert resp is not None
    bot = session["messages"][-1]
    assert bot["concierge_intent"] == "app_about"
    assert "chat-status-card" in bot["content"]
    assert "一般用医薬品（OTC）の相談窓口です" not in bot["content"]


@patch("src.core.llm_client.chat_completion_create")
def test_self_intro_via_meta_triage(mock_llm):
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "app_about", "confidence": 0.95}'))]
    )
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    try_concierge_response(
        session,
        client,
        None,
        "自己紹介して",
        "自己紹介して",
        {"category": "Other", "confidence": 0.99},
        MagicMock(),
    )
    bot = session["messages"][-1]
    assert bot["concierge_intent"] == "app_about"
    assert "一般用医薬品（OTC）の相談窓口です" not in bot["content"]


@patch("src.core.llm_client.chat_completion_create")
def test_concierge_runs_when_user_already_appended_in_pipeline(mock_llm):
    """append_user_message_if_needed 後でも Concierge が応答する。"""
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "self_intro", "confidence": 0.95}'))]
    )
    session = {
        "messages": [{"type": "user", "content": "あんたについて教えて"}],
        "user_attributes": {},
    }
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = try_concierge_response(
        session,
        client,
        None,
        "あんたについて教えて",
        "あんたについて教えて",
        {"category": "Other", "confidence": 0.99},
        MagicMock(),
    )
    assert resp is not None
    bots = [m for m in session["messages"] if m.get("type") == "bot"]
    assert len(bots) == 1
    assert bots[0].get("concierge") is True


def test_physical_triage_skips_concierge():

    session = {"messages": [], "user_attributes": {}}

    client = MagicMock()

    client.client_ip = "127.0.0.1"

    client.user_agent = "test"



    resp = try_concierge_response(

        session,

        client,

        None,

        "頭が痛い",

        "頭が痛い",

        {"category": "Physical", "confidence": 0.95},

        MagicMock(),

    )

    assert resp is None

    assert len(session["messages"]) == 0


@patch("src.agents.concierge_agent.concierge_chat")
@patch("src.core.llm_client.chat_completion_create")
def test_doc_privacy_via_meta_triage(mock_meta_chat, mock_concierge_chat):
    mock_meta_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent": "doc_privacy", "confidence": 0.95}'))]
    )
    mock_concierge_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="個人を直接特定できる情報は収集しません。詳細はプライバシーポリシーに記載があります。"
                )
            )
        ]
    )
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    resp = try_concierge_response(
        session,
        client,
        None,
        "プライバシーポリシーを教えて",
        "プライバシーポリシーを教えて",
        {"category": "Other", "confidence": 0.99},
        MagicMock(),
    )
    assert resp is not None
    bot = session["messages"][-1]
    assert bot["concierge_intent"] == "doc_privacy"
    assert bot["content_format"] == "text"
    assert "収集" in bot["content"]


@patch("src.agents.concierge_agent.generate_greeting_text", return_value=("またこんにちは", True))
def test_concierge_replies_on_immediate_regreeting(mock_greeting):
    """直前ターンと同一挨拶の二重送信でも Concierge が再応答する。"""
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "返信", "concierge": True},
        ],
        "user_attributes": {},
    }
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    with patch("src.handlers.chat.chat_concierge_route.save_session_to_db"):
        resp = try_concierge_response(
            session,
            client,
            "sid-test",
            "こんにちは",
            "こんにちは",
            {"category": "Other", "confidence": 0.99, "concierge_intent": "greeting"},
            MagicMock(),
        )

    assert resp is not None
    body, status = resp
    assert status == 200
    assert body.get("duplicate_skip") is not True
    assert len(session["messages"]) == 4
    assert session["messages"][-2]["type"] == "user"
    assert session["messages"][-2]["content"] == "こんにちは"
    assert session["messages"][-1]["type"] == "bot"
    assert session["messages"][-1].get("greeting") is True
    mock_greeting.assert_called_once()

