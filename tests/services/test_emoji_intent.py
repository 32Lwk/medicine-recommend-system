"""emoji_intent サービスのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.emoji_intent import (
    _parse_emoji_intent_json,
    build_offensive_emoji_fallback_text,
    build_emoji_unknown_ack_text,
    classify_emoji_intent_llm,
)


def test_parse_emoji_intent_json():
    intent, conf = _parse_emoji_intent_json('{"intent": "emotional", "confidence": 0.95}')
    assert intent == "emotional"
    assert conf == 0.95


def test_offensive_fallback_is_short_and_empathetic():
    from src.services.emoji_intent import _OFFENSIVE_EMOJI_FALLBACKS

    for text in _OFFENSIVE_EMOJI_FALLBACKS:
        assert "攻撃" not in text
        assert "侮辱" not in text
        assert len(text) <= 180
        assert (
            "お気持ち" in text
            or "受け止め" in text
            or "お聞かせ" in text
            or "お声がけ" in text
            or "お手伝い" in text
        )


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
