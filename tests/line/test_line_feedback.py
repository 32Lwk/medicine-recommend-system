"""LINE Quick Reply / postback フィードバックのテスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.flex_messages import resolve_medicine_hero_url
from src.handlers.line.line_feedback import (
    _load_pending_context,
    attach_feedback_quick_reply,
    handle_line_feedback_postback,
    parse_feedback_postback,
    prepare_line_messages_with_feedback,
    register_line_feedback_pending,
)
from src.services.feedback_submit import submit_feedback_record


def test_resolve_medicine_hero_url_always_placeholder(monkeypatch):
    monkeypatch.delenv("PUBLIC_SITE_URL", raising=False)
    monkeypatch.delenv("LINE_HERO_PLACEHOLDER_URL", raising=False)
    url = resolve_medicine_hero_url({})
    assert url.endswith("/static/line/medicine-noimage-hero.png")
    assert url.startswith("https://")


def test_parse_feedback_postback():
    assert parse_feedback_postback("mrcfb|pos|abc12345") == ("positive_feedback", "abc12345")
    assert parse_feedback_postback("mrcfb|neg|abc12345") == ("negative_feedback", "abc12345")
    assert parse_feedback_postback("invalid") is None


def test_attach_feedback_quick_reply_on_last_message():
    msgs = [{"type": "flex", "altText": "a"}, {"type": "flex", "altText": "b"}]
    ui = {"feedback_positive_label": "👍", "feedback_negative_label": "👎"}
    out = attach_feedback_quick_reply(msgs, "deadbeef", ui)
    assert "quickReply" not in out[0]
    assert out[1]["quickReply"]["items"][0]["action"]["data"] == "mrcfb|pos|deadbeef"


@patch("src.handlers.line.line_feedback.save_session_to_db")
@patch("src.handlers.line.line_feedback.get_session_from_db", return_value={})
def test_pending_survives_stale_db_session(mock_get, mock_save):
    key = register_line_feedback_pending(
        "line:U1",
        user_message="頭痛",
        ai_response="おすすめ",
    )
    mock_get.return_value = {"session_id": "line:U1", "line_feedback_pending": {}}
    ctx = _load_pending_context("line:U1", key)
    assert ctx is not None
    assert ctx["user_message"] == "頭痛"


@patch("src.handlers.line.line_feedback.save_session_to_db")
@patch("src.handlers.line.line_feedback.get_session_from_db", return_value={})
def test_prepare_line_messages_registers_pending(mock_get, mock_save):
    bot = {"type": "bot", "content": "<p>ok</p>"}
    flex = [{"type": "flex", "altText": "おすすめ"}]
    with patch(
        "src.handlers.line.line_feedback.register_line_feedback_pending",
        return_value="cafebabe",
    ) as mock_reg:
        out = prepare_line_messages_with_feedback(
            flex,
            sid="line:U1",
            user_message="頭痛",
            bot_message=bot,
            lang="ja",
        )
    mock_reg.assert_called_once()
    assert out[0]["quickReply"]["items"][1]["action"]["data"] == "mrcfb|neg|cafebabe"


@patch("src.handlers.line.line_feedback.submit_feedback_record", return_value={"status": "success", "feedback_id": 1})
@patch("src.handlers.line.line_feedback._load_pending_context")
@patch("src.handlers.line.line_session.prime_line_session")
@patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token")
def test_handle_postback_submits_positive(mock_prime, mock_pending, mock_submit):
    mock_prime.return_value = {"username": "LINEユーザー", "detected_language": "ja"}
    mock_pending.return_value = {"user_message": "頭痛", "ai_response": "おすすめ"}
    with patch("src.handlers.line.line_reply.reply_messages", new_callable=AsyncMock) as mock_reply:
        asyncio.run(handle_line_feedback_postback("U1", "mrcfb|pos|abc12345", reply_token="tok"))
    mock_submit.assert_called_once()
    assert mock_submit.call_args.kwargs["report_type"] == "positive_feedback"
    mock_reply.assert_awaited_once()


@patch("src.services.feedback_submit.save_session_to_db")
@patch("src.services.feedback_submit.get_session_from_db", return_value={})
@patch("src.services.feedback_submit.get_database", return_value=None)
@patch("src.services.feedback_submit.is_development_runtime", return_value=True)
@patch("src.services.feedback_store.save_feedback_dev", return_value=7)
def test_submit_feedback_record_dev_fallback(mock_save_dev, *_mocks):
    result = submit_feedback_record(
        report_type="positive_feedback",
        session_id="line:U1",
        username="LINEユーザー",
        user_message="頭痛",
        ai_response="おすすめ",
    )
    assert result["feedback_id"] == 7
    mock_save_dev.assert_called_once()
