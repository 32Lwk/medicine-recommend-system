"""ConciergeAgent 応答ペイロードのテスト"""
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import (
    _GREETING_PROMPT_REQUIREMENTS,
    _GREETING_SYSTEM_PROMPT,
    build_concierge_payload,
    count_same_greeting_exchange_rounds,
    format_concierge_context_block,
    generate_greeting_text,
    infer_is_first_greeting_contact,
    resolve_concierge_intent,
)


def test_greeting_prompt_prioritizes_trust_and_ichiyaku_wording():
    assert "市販薬" in _GREETING_PROMPT_REQUIREMENTS
    assert "OTC" in _GREETING_PROMPT_REQUIREMENTS and "使わない" in _GREETING_PROMPT_REQUIREMENTS
    assert "ミラーリング" in _GREETING_PROMPT_REQUIREMENTS
    assert "寄り添" in _GREETING_PROMPT_REQUIREMENTS
    assert "傾聴" in _GREETING_PROMPT_REQUIREMENTS
    assert "おい" in _GREETING_PROMPT_REQUIREMENTS or "ねえ" in _GREETING_PROMPT_REQUIREMENTS
    assert "会話の継続" in _GREETING_PROMPT_REQUIREMENTS
    assert "また来てくれて" in _GREETING_PROMPT_REQUIREMENTS
    assert "初回接触" in _GREETING_PROMPT_REQUIREMENTS
    assert "優先順位" in _GREETING_PROMPT_REQUIREMENTS
    assert "80〜180" in _GREETING_PROMPT_REQUIREMENTS
    assert "例文はそのままコピーせず" in _GREETING_PROMPT_REQUIREMENTS
    assert "煽" in _GREETING_PROMPT_REQUIREMENTS
    assert "やわらかく書いて" in _GREETING_PROMPT_REQUIREMENTS
    assert "お気軽" in _GREETING_PROMPT_REQUIREMENTS
    assert "ミラーリング" in _GREETING_SYSTEM_PROMPT


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_llm_prompt_includes_first_contact_flag(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="やあ！"))]
    mock_chat.return_value = mock_resp
    generate_greeting_text(MagicMock(), "やあ", history=[])
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "【初回接触】" in user_prompt
    assert "はい" in user_prompt
    assert "初回接触の追加要件" in user_prompt

    history = [
        {"type": "bot", "greeting": True, "content": "こんにちは"},
    ]
    generate_greeting_text(MagicMock(), "おい", history=history)
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "いいえ" in user_prompt.split("【初回接触】")[1].split("\n")[1]
    assert "継続接触の追加要件" in user_prompt
    assert "【会話の文脈】" in user_prompt


def test_count_same_greeting_exchange_rounds():
    history = [
        {"type": "user", "content": "やあ"},
        {"type": "bot", "content": "1", "greeting": True},
        {"type": "user", "content": "やあ"},
        {"type": "bot", "content": "2", "greeting": True},
        {"type": "user", "content": "やあ"},
    ]
    assert count_same_greeting_exchange_rounds(history, "やあ") == 3


def test_format_concierge_context_block_warns_on_repeated_greeting():
    history = [
        {"type": "user", "content": "やあ"},
        {
            "type": "bot",
            "content": "sage_status",
            "greeting": True,
            "diagnosis": {"kind": "concierge_greeting", "message": "やあ、こんにちは"},
        },
        {"type": "user", "content": "やあ"},
    ]
    block = format_concierge_context_block(history, "やあ", mode="greeting")
    assert "2 回目" in block
    assert "やあ、こんにちは" in block

    triple = history + [
        {"type": "bot", "content": "また来て", "greeting": True},
        {"type": "user", "content": "やあ"},
    ]
    block3 = format_concierge_context_block(triple, "やあ", mode="greeting")
    assert "3 回目" in block3
    assert "また来てくれて" in block3


@patch("src.agents.concierge_agent.concierge_chat")
def test_chitchat_prompt_includes_context_block(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="そうですね。"))]
    mock_chat.return_value = mock_resp
    from src.agents.concierge_agent import generate_chitchat_text

    history = [
        {"type": "user", "content": "暇だな"},
        {"type": "bot", "content": "お話ありがとうございます", "concierge": True},
    ]
    generate_chitchat_text(MagicMock(), "今日は暑いね", history=history)
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "【会話の文脈】" in user_prompt
    assert "【会話履歴（参考）】" in user_prompt
    assert "暇だな" in user_prompt


def test_infer_is_first_greeting_contact():
    assert infer_is_first_greeting_contact([]) is True
    assert infer_is_first_greeting_contact(None) is True
    assert infer_is_first_greeting_contact(
        [{"type": "bot", "greeting": True, "content": "hi"}]
    ) is False
    assert infer_is_first_greeting_contact(
        [
            {
                "type": "bot",
                "content": "sage_status",
                "diagnosis": {"kind": "concierge_greeting"},
            }
        ]
    ) is False
    assert infer_is_first_greeting_contact(
        [{"type": "user", "content": "頭痛"}]
    ) is True


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_llm_prompt_includes_brand_guidelines(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="こんにちは。"))]
    mock_chat.return_value = mock_resp
    generate_greeting_text(MagicMock(), "やあ")
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "市販薬" in user_prompt
    assert "ミラーリング" in user_prompt
    assert "寄り添" in user_prompt
    assert "会話の継続" in user_prompt
    system_prompt = mock_chat.call_args[0][2][0]["content"]
    assert "ミラーリング" in system_prompt


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_llm_prompt_expands_sage_status_history(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="お声がけありがとうございます。何かお困りでしょうか？"))]
    mock_chat.return_value = mock_resp
    history = [
        {"type": "user", "content": "やー"},
        {
            "type": "bot",
            "content": "sage_status",
            "diagnosis": {
                "render": "sage_status",
                "title": "ご挨拶",
                "message": "やあ、市販薬の相談ツールです。",
            },
        },
    ]
    generate_greeting_text(MagicMock(), "おい", history=history)
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "市販薬の相談ツールです" in user_prompt
    assert "sage_status" not in user_prompt


@patch("src.agents.concierge_agent.concierge_chat")
def test_greeting_payload_uses_llm_by_default(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "やあ、こんにちは。こちらは市販薬の相談窓口です。"
                    "頭痛やのどの痛みなど、お気軽にご相談ください。"
                )
            )
        )
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
    assert "やわらかく" not in p["content"]
    assert "具体的に" not in p["content"]
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
