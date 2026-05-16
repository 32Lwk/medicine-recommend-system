"""ConciergeAgent 応答ペイロードのテスト"""
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import build_concierge_payload, resolve_concierge_intent


def test_greeting_payload_no_llm():
    p = build_concierge_payload("greeting", "こんにちは", MagicMock())
    assert p["content_format"] == "text"
    assert p["llm_used"] is False
    assert len(p["content"]) > 5
    assert p.get("greeting") is True


def test_architecture_payload_card():
    p = build_concierge_payload("architecture", "マルチエージェント？", MagicMock())
    assert p["content_format"] == "status_card"
    assert "TriageAgent" in p["content"]


def test_redirect_after_chitchat_turns():
    session = {"concierge_state": {"off_topic_turns": 2}}
    assert resolve_concierge_intent("今日はいい天気ですね", session) == "redirect"


def test_doc_operator_returns_card_with_links():
    p = build_concierge_payload("doc_operator", "運営者の連絡先は？", MagicMock())
    assert p["llm_used"] is False
    assert p["content_format"] == "status_card"
    assert "川嶋" in p["content"]
    assert 'href="https://forms.gle/UB8kZHd4VHenmRUN6"' in p["content"]
    assert 'href="https://github.com/32Lwk"' in p["content"]
    assert "weary-scoots.7y@icloud.com" in p["content"]
    assert "診断や処方" not in p["content"]


@patch("src.agents.concierge_agent.concierge_chat")
def test_chitchat_uses_llm(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="そうですね。お薬のことでしたらどうぞ。"))]
    mock_chat.return_value = mock_resp
    p = build_concierge_payload("chitchat", "暇だな", MagicMock())
    assert p["llm_used"] is True
