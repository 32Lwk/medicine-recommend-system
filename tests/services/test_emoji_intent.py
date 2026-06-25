"""emoji_intent サービスのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.emoji_intent import (
    _parse_emoji_intent_json,
    build_emoji_soft_intro_text,
    build_emoji_unknown_ack_text,
    classify_emoji_intent_llm,
)


def test_parse_emoji_intent_json():
    intent, conf = _parse_emoji_intent_json('{"intent": "emotional", "confidence": 0.95}')
    assert intent == "emotional"
    assert conf == 0.95


def test_soft_intro_no_insult_mention():
    text = build_emoji_soft_intro_text()
    assert "攻撃" not in text
    assert "侮辱" not in text
    assert "市販薬" in text or "一般用医薬品" in text
    assert len(text) > 200


def test_unknown_ack_mentions_text_prompt():
    text = build_emoji_unknown_ack_text()
    assert "テキスト" in text


@patch("src.core.llm_client.chat_completion_create")
def test_classify_emoji_intent_llm(mock_create):
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='{"intent": "greeting", "confidence": 0.9}'))
    ]
    mock_create.return_value = mock_resp
    intent, conf = classify_emoji_intent_llm(MagicMock(), "👋", session_id="line:U1")
    assert intent == "greeting"
    assert conf == 0.9
    assert mock_create.call_args.kwargs["model_role"] == "emoji_intent"
