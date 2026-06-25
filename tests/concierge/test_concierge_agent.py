"""ConciergeAgent 応答ペイロードのテスト"""
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import (
    _GREETING_PROMPT_REQUIREMENTS,
    _GREETING_SYSTEM_PROMPT,
    _extract_substantive_user_topics,
    _greeting_service_context_block,
    build_concierge_payload,
    build_short_callout_greeting_text,
    count_same_greeting_exchange_rounds,
    format_concierge_context_block,
    generate_greeting_text,
    greeting_response_too_short,
    greeting_responses_too_similar,
    greeting_response_mirrors_provocative_callout,
    infer_is_first_greeting_contact,
    is_short_impatient_callout,
    resolve_concierge_intent,
    sanitize_greeting_response,
)


def test_greeting_prompt_is_concise_and_principle_based():
    assert "市販薬" in _GREETING_PROMPT_REQUIREMENTS
    assert "60〜120" in _GREETING_PROMPT_REQUIREMENTS
    assert "直前の bot 返答" in _GREETING_PROMPT_REQUIREMENTS
    assert "ミラーリング" in _GREETING_PROMPT_REQUIREMENTS
    assert "例（短い呼びかけ" not in _GREETING_PROMPT_REQUIREMENTS
    assert "禁止（不自然" not in _GREETING_PROMPT_REQUIREMENTS
    assert "自然な続き" in _GREETING_SYSTEM_PROMPT


def test_greeting_service_context_includes_policy_and_limitations():
    block = _greeting_service_context_block()
    assert "診断・処方" in block
    assert "本ツールについて" in block
    assert "制限:" in block


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_llm_prompt_includes_first_contact_flag(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="やあ！"))]
    mock_create.return_value = mock_resp
    generate_greeting_text(MagicMock(), "やあ", history=[])
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "【初回接触】" in user_prompt
    assert "はい" in user_prompt
    assert "【今回の要点】" in user_prompt

    history = [
        {"type": "bot", "greeting": True, "content": "こんにちは"},
    ]
    generate_greeting_text(MagicMock(), "やあ", history=history)
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "いいえ" in user_prompt.split("【初回接触】")[1].split("\n")[1]
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
        [{"type": "user", "content": "やあ"}]
    ) is True
    assert infer_is_first_greeting_contact(
        [{"type": "user", "content": "頭痛"}]
    ) is False
    assert infer_is_first_greeting_contact(
        [
            {"type": "user", "content": "花粉症で頭痛"},
            {"type": "bot", "content": "推奨結果"},
            {"type": "user", "content": "おい"},
        ],
        user_text="おい",
    ) is False


def test_extract_substantive_user_topics_excludes_callouts():
    msgs = [
        {"type": "user", "content": "やあ"},
        {"type": "bot", "content": "hi", "greeting": True},
        {"type": "user", "content": "おい"},
        {"type": "user", "content": "花粉症で頭痛"},
    ]
    assert _extract_substantive_user_topics(msgs) == ["花粉症で頭痛"]


def test_is_short_impatient_callout():
    assert is_short_impatient_callout("おい")
    assert is_short_impatient_callout("  ねえ  ")
    assert not is_short_impatient_callout("こんにちは")


def test_greeting_response_too_short():
    assert greeting_response_too_short("おい、どう？", is_first=True)
    assert not greeting_response_too_short(
        "お声がけありがとうございます。こちらは市販薬の相談窓口です。頭痛やのどの痛み、鼻水、胃の不調など、お気軽にご相談ください。",
        is_first=True,
    )


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_llm_uses_greeting_role_and_temperature(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="こんにちは。"))]
    mock_create.return_value = mock_resp
    generate_greeting_text(MagicMock(), "やあ", history=[])
    kwargs = mock_create.call_args.kwargs
    assert kwargs.get("model_role") == "concierge_greeting"
    assert kwargs.get("temperature") is not None
    assert kwargs.get("max_tokens") >= 256


def test_greeting_responses_too_similar_detects_same_opening():
    a = "お声がけありがとうございます。何かお困りでしょうか？"
    b = "お声がけありがとうございます。続きがあればお聞かせください。"
    assert greeting_responses_too_similar(a, b)


def test_greeting_responses_too_similar():
    a = "どうされましたか。焦らなくて大丈夫です、困っていることをそのまま教えてください。"
    assert greeting_responses_too_similar(a, a)
    assert greeting_responses_too_similar(a, a.replace("。", ""))
    assert not greeting_responses_too_similar(
        "お声がけありがとうございます。何かお困りでしょうか？",
        "はい、どうぞ。続きがあればお聞かせください。",
    )


def test_sanitize_greeting_response_strips_rude_mirroring():
    raw = "おい、こちらは市販薬の相談窓口です。お気軽にどうぞ。"
    cleaned = sanitize_greeting_response(raw, "おい")
    assert not cleaned.startswith("おい")


def test_sanitize_greeting_response_strips_rude_mirroring_exclamation():
    from src.agents.concierge_agent import _GREETING_SANITIZE_OPENINGS

    raw = (
        "おい！元気かい？市販薬について何か気になることがあれば、ぜひ教えてね。"
        "風邪の症状や頭痛、アレルギーの対策など、具体的にお話ししてもらえればお手伝いできるよ。"
    )
    cleaned = sanitize_greeting_response(raw, "おい")
    assert not cleaned.startswith("おい")
    assert any(cleaned.startswith(o) for o in _GREETING_SANITIZE_OPENINGS)


def test_greeting_response_mirrors_provocative_callout_detects_exclamation():
    assert greeting_response_mirrors_provocative_callout("おい！元気かい？", "おい")
    assert greeting_response_mirrors_provocative_callout(
        "承知しました。元気かい？市販薬について教えてね。",
        "おい",
    )
    assert not greeting_response_mirrors_provocative_callout(
        "お声がけありがとうございます。お困りのことがあればお聞かせください。",
        "おい",
    )


def test_sanitize_greeting_response_replaces_hai_dozo_on_callout():
    raw = "はい、どうぞ。気になる症状を教えてください。"
    cleaned = sanitize_greeting_response(raw, "おい")
    assert not cleaned.startswith("はい、どうぞ")
    assert cleaned.endswith("気になる症状を教えてください。")


def test_sanitize_greeting_response_replaces_kochira_ni_imasu():
    raw = "はい、こちらにいます。花粉症の頭痛のことも含めて、お聞かせください。"
    cleaned = sanitize_greeting_response(raw, "おい")
    assert "こちらにいます" not in cleaned
    assert "花粉症" in cleaned
    assert not cleaned.startswith("はい、こちらにいます")


@patch("src.core.llm_client.chat_completion_create")
def test_short_callout_retries_when_same_as_last_bot(mock_create):
    duplicate = "どうされましたか。焦らなくて大丈夫です、困っていることをそのまま教えてください。"
    alt = (
        "呼びかけありがとうございます。"
        "続きのご相談があれば、気になる症状やいつからかを短くでもお聞かせください。"
        "市販薬の候補を一緒に見ていきます。"
    )
    mock_resp_dup = MagicMock()
    mock_resp_dup.choices = [MagicMock(message=MagicMock(content=duplicate))]
    mock_resp_alt = MagicMock()
    mock_resp_alt.choices = [MagicMock(message=MagicMock(content=alt))]
    mock_create.side_effect = [mock_resp_dup, mock_resp_alt]
    history = [
        {"type": "user", "content": "やあ"},
        {"type": "bot", "greeting": True, "content": duplicate},
    ]
    text, used = generate_greeting_text(MagicMock(), "おい", history=history)
    assert mock_create.call_count == 2
    assert used is True
    assert text == alt


@patch("src.core.llm_client.chat_completion_create")
def test_short_callout_uses_llm(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "お声がけありがとうございます。花粉症の頭痛の続きでしたら、"
                    "いつ頃から・どのくらい続いているかも含めて、お気軽にお聞かせください。"
                )
            )
        )
    ]
    mock_create.return_value = mock_resp
    history = [
        {"type": "user", "content": "花粉症で頭痛"},
        {"type": "bot", "content": "推奨結果"},
    ]
    text, used = generate_greeting_text(MagicMock(), "おい", history=history)
    assert mock_create.call_count == 1
    assert used is True
    assert "花粉症" in text
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "本ツールについて" in user_prompt


def test_build_short_callout_greeting_text_avoids_duplicate():
    prev = "お声がけありがとうございます。何かお困りのことがあれば、お聞かせください。"
    alt = build_short_callout_greeting_text(is_first=False, exclude=prev)
    assert not greeting_responses_too_similar(alt, prev)


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_llm_prompt_includes_brand_guidelines(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="こんにちは。"))]
    mock_create.return_value = mock_resp
    generate_greeting_text(MagicMock(), "やあ")
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "市販薬" in user_prompt
    system_prompt = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "自然な続き" in system_prompt


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_llm_prompt_expands_sage_status_history(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="お声がけありがとうございます。何かお困りでしょうか？"))]
    mock_create.return_value = mock_resp
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
    generate_greeting_text(MagicMock(), "やあ", history=history)
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "市販薬の相談ツールです" in user_prompt
    assert "sage_status" not in user_prompt


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_payload_uses_llm_by_default(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "やあ、こんにちは。こちらは市販薬の相談窓口です。"
                    "頭痛やのどの痛み、鼻水、胃の不調など、気になる症状をお気軽にご相談ください。"
                )
            )
        )
    ]
    mock_create.return_value = mock_resp
    client = MagicMock()
    p = build_concierge_payload("greeting", "やあ", client)
    assert p["content_format"] == "text"
    assert p["llm_used"] is True
    assert p.get("greeting") is True
    mock_create.assert_called_once()


@patch("src.core.llm_client.chat_completion_create")
def test_greeting_payload_falls_back_to_template_on_llm_failure(mock_create):
    mock_create.side_effect = RuntimeError("llm unavailable")
    client = MagicMock()
    p = build_concierge_payload("greeting", "やあ", client)
    assert p["llm_used"] is False
    assert p.get("greeting") is True
    mock_create.assert_called_once()


@patch("src.agents.concierge_agent.concierge_chat")
def test_meta_payload_has_no_hints(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="説明です。"))]
    )
    p = build_concierge_payload("architecture", "仕組みは？", MagicMock())
    assert p["sage_diagnosis"].get("hints") == []
    assert p.get("line_flex", {}).get("hints") == []


@patch("src.agents.concierge_agent.concierge_chat")
def test_architecture_multi_agent_prompt_avoids_who_lead(mock_chat):
    captured: dict = {}

    def _capture(client, path, messages, **kwargs):
        captured["user"] = messages[-1]["content"]
        return MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=(
                            "マルチエージェントは、役割ごとに分かれた担当が連携する仕組みです。"
                            "このサービスでは、最初に内容を振り分け、症状相談・案内・店舗案内などを"
                            "それぞれの担当に渡します。"
                        )
                    )
                )
            ]
        )

    mock_chat.side_effect = _capture
    p = build_concierge_payload("architecture", "マルチエージェントは何？", MagicMock())
    prompt = captured["user"]
    assert "担当宣言から答えを始めない" in prompt
    assert "いま誰が答えているか" in prompt
    assert "第一文は「いまの案内は" not in prompt
    assert not p["sage_diagnosis"]["message"].startswith("いまの案内は")


@patch("src.agents.concierge_agent.concierge_chat")
def test_architecture_payload_card(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="返信はAIが生成し、TriageAgent が振り分けます。"
                )
            )
        ]
    )
    p = build_concierge_payload("architecture", "マルチエージェント？", MagicMock())
    assert p["content_format"] == "status_card"
    assert p["llm_used"] is True
    assert p.get("line_flex") is not None
    assert "TriageAgent" in p["content"]


@patch("src.agents.concierge_agent.concierge_chat")
def test_meta_llm_retries_then_falls_back_to_card(mock_chat):
    mock_chat.side_effect = [RuntimeError("llm down"), RuntimeError("llm down again")]
    p = build_concierge_payload("capabilities", "できることは？", MagicMock())
    assert p["llm_used"] is False
    assert "chat-status-card" in p["content"]
    assert mock_chat.call_count == 2


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


@patch("src.agents.concierge_agent.concierge_chat")
def test_thanks_llm_prompt_includes_user_text(mock_chat):
    from src.agents.concierge_agent import generate_thanks_text

    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content="こちらこそありがとうございます。お役に立てて何よりです。"
            )
        )
    ]
    mock_chat.return_value = mock_resp
    text, used = generate_thanks_text(MagicMock(), "ありがとうございます")
    assert used is True
    assert "ありがとう" in text
    user_prompt = mock_chat.call_args[0][2][1]["content"]
    assert "【ユーザーの感謝】" in user_prompt
    assert "ありがとうございます" in user_prompt
    assert "ミラーリング" in user_prompt


@patch("src.agents.concierge_agent.concierge_chat")
def test_thanks_payload_uses_llm(mock_chat):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content="どういたしまして！また何かあればどうぞ。"))
    ]
    mock_chat.return_value = mock_resp
    p = build_concierge_payload("thanks", "ありがとう", MagicMock())
    assert p["llm_used"] is True
    assert p["concierge_intent"] == "thanks"
    assert "どういたしまして" in p["content"]


def test_format_concierge_context_block_thanks_mode():
    block = format_concierge_context_block([], "ありがとうございます", mode="thanks")
    assert "ありがとうございます" in block
    assert "丁寧さ" in block


def test_build_thanks_text_fallback_mirrors_formality():
    from src.services.concierge_templates import build_thanks_text

    casual = build_thanks_text("ありがとう")
    formal = build_thanks_text("ありがとうございます")
    assert "どういたしまして" in casual
    assert "こちらこそありがとうございます" in formal
    assert casual != formal
