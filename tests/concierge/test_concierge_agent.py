"""ConciergeAgent 応答ペイロードのテスト"""
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import build_concierge_payload, resolve_concierge_intent


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_payload_uses_llm_by_default(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content="やあ！市販薬の相談ならお気軽にどうぞ。"))
    ]
    mock_chat.return_value = mock_resp
    client = MagicMock()
    p = build_concierge_payload("greeting", "やあ", client)
    assert p["content_format"] == "text"
    assert p["llm_used"] is True
    assert p.get("greeting") is True
    mock_chat.assert_called_once()


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_payload_falls_back_to_template_on_llm_failure(mock_chat):
    mock_chat.side_effect = RuntimeError("llm unavailable")
    client = MagicMock()
    p = build_concierge_payload("greeting", "やあ", client)
    assert p["llm_used"] is False
    assert p.get("greeting") is True
    mock_chat.assert_called_once()


def test_architecture_payload_card():
    p = build_concierge_payload("architecture", "マルチエージェント？", MagicMock())
    assert p["content_format"] == "status_card"
    assert "TriageAgent" in p["content"]


@patch("src.agents.concierge_agent.classify_concierge_intent", return_value="chitchat")
def test_redirect_after_chitchat_turns(_mock_classify):
    session = {"concierge_state": {"off_topic_turns": 2}}
    assert resolve_concierge_intent("weather small talk", session) == "redirect"


@patch("src.agents.concierge_agent.concierge_chat")
def test_doc_operator_returns_status_card_with_links(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "本ツールは試験運用のβ版です。"
                    "個人名や所属は開示していません。"
                )
            )
        )
    ]
    mock_chat.return_value = mock_resp
    client = MagicMock()
    p = build_concierge_payload("doc_operator", "運営者の連絡先は？", client)
    assert p["llm_used"] is True
    assert p["content_format"] == "status_card"
    assert "chat-status-card--notice" in p["content"]
    assert "お問い合わせ・試験運用について" in p["content"]
    assert "川嶋" not in p["content"]
    assert "名古屋大学" not in p["content"]
    assert 'href="mailto:weary-scoots.7y@icloud.com"' in p["content"]
    assert 'href="https://forms.gle/UB8kZHd4VHenmRUN6"' in p["content"]
    assert "診断や処方" not in p["content"]
    mock_chat.assert_called_once()
    assert mock_chat.call_args.kwargs.get("allow_stream") is False


@patch("src.agents.concierge_agent.concierge_chat")
def test_chitchat_uses_llm(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="そうですね。お薬のことでしたらどうぞ。"))]
    mock_chat.return_value = mock_resp
    p = build_concierge_payload("chitchat", "暇だな", MagicMock())
    assert p["llm_used"] is True
