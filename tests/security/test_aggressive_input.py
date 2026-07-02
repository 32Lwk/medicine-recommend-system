"""攻撃的入力検出と境界案内ルートのテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_inappropriate_route import (
    detect_inappropriate_message,
    handle_inappropriate_message_if_detected,
)
from src.security.aggressive_input import (
    AGGRESSIVE_INPUT_NOTICE_MESSAGE,
    detect_aggressive_expression,
    is_aggressive_expression,
    is_non_absolute_aggressive_expression,
)
from src.security.input_block_responses import NOTICE_BY_CATEGORY
from src.services.concierge_intent import infer_structural_concierge_intent


def test_detect_kill_threat():
    assert detect_inappropriate_message("殺すぞ")
    assert is_aggressive_expression("殺すぞ")[0]
    assert is_non_absolute_aggressive_expression("殺すぞ")[0]


def test_detect_numeric_slang_absolute_block_not_inappropriate_route():
    assert is_aggressive_expression("69")[0]
    assert not is_non_absolute_aggressive_expression("69")[0]
    assert not detect_inappropriate_message("69")


def test_symptom_slang_kill_not_aggressive():
    assert not detect_inappropriate_message("頭痛が殺す")
    assert not is_non_absolute_aggressive_expression("頭痛が殺す")[0]


def test_absolute_block_is_aggressive_but_not_inappropriate_route():
    assert is_aggressive_expression("しね")[0]
    assert not is_non_absolute_aggressive_expression("しね")[0]


def test_structural_intent_skips_aggressive_short_text():
    assert infer_structural_concierge_intent("殺すぞ") is None
    assert infer_structural_concierge_intent("こんにちは") == "greeting"


@patch("src.handlers.chat.chat_inappropriate_route.save_session_to_db")
def test_handle_returns_aggressive_notice(mock_save):
    session = {"messages": []}
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"
    resp = handle_inappropriate_message_if_detected(
        session, client, "sid", "殺すぞ", "殺すぞ", MagicMock()
    )
    assert resp is not None
    assert resp[0]["status"] == "ok"
    assert resp[0]["response"] == AGGRESSIVE_INPUT_NOTICE_MESSAGE
    assert len(session["messages"]) == 2
    assert session["messages"][0]["content"] == "殺すぞ"
    bot = session["messages"][1]
    assert bot["type"] == "bot"
    assert bot["diagnosis"]["kind"] == "aggressive_input"
    assert bot["diagnosis"]["message"] == AGGRESSIVE_INPUT_NOTICE_MESSAGE


def test_detect_aggressive_expression_helper():
    assert detect_aggressive_expression("殺すぞ")
    assert not detect_aggressive_expression("こんにちは")
    assert not detect_aggressive_expression("レイプ")


def test_sex_uses_sexual_content_message_not_aggressive():
    from src.security.input_block_responses import match_input_block

    notice = match_input_block("sex")
    assert notice is not None
    assert notice.message != AGGRESSIVE_INPUT_NOTICE_MESSAGE
    assert notice.message == NOTICE_BY_CATEGORY["sexual_content"]
