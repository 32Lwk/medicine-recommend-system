"""LINE Quick Reply / postback フィードバックのテスト。"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.line.flex_messages import resolve_medicine_hero_url
from src.handlers.line.line_feedback import (
    _load_pending_context,
    attach_feedback_quick_reply,
    handle_line_feedback_postback,
    is_line_feedback_display_text,
    parse_feedback_postback,
    prepare_line_messages_with_feedback,
    register_line_feedback_pending,
    should_offer_line_feedback,
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


def test_is_line_feedback_display_text():
    assert is_line_feedback_display_text("役に立った")
    assert is_line_feedback_display_text(" 役に立たなかった ")
    assert is_line_feedback_display_text("Helpful")
    assert not is_line_feedback_display_text("頭が痛い")
    assert not is_line_feedback_display_text("こんにちは")


def test_attach_feedback_quick_reply_on_last_message():
    msgs = [{"type": "flex", "altText": "a"}, {"type": "flex", "altText": "b"}]
    ui = {"feedback_positive_label": "👍", "feedback_negative_label": "👎"}
    out = attach_feedback_quick_reply(msgs, "deadbeef", ui)
    assert "quickReply" not in out[0]
    assert out[1]["quickReply"]["items"][0]["action"]["data"] == "mrcfb|pos|deadbeef"


@patch("src.handlers.line.line_feedback._persist_pending_map")
def test_register_line_feedback_pending_stores_entry(mock_persist):
    key = register_line_feedback_pending(
        "line:U1",
        user_message="頭痛",
        ai_response="おすすめ",
    )
    mock_persist.assert_called_once()
    pending = mock_persist.call_args[0][1]
    assert key in pending
    assert pending[key]["user_message"] == "頭痛"


@patch("src.handlers.line.line_feedback._load_pending_map")
def test_pending_loads_from_db_when_memory_empty(mock_load):
    mock_load.return_value = {
        "abc12345": {"user_message": "頭痛", "ai_response": "おすすめ", "ts": time.time()},
    }
    ctx = _load_pending_context("line:U1", "abc12345")
    assert ctx is not None
    assert ctx["user_message"] == "頭痛"


@patch("src.handlers.line.line_feedback._persist_pending_map")
def test_prepare_line_messages_registers_pending(mock_persist):
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


@patch("src.handlers.line.line_feedback.submit_feedback_async")
@patch("src.handlers.line.line_feedback._load_pending_context")
@patch("src.handlers.line.line_session.prime_line_session")
@patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token")
def test_handle_postback_submits_positive(mock_prime, mock_pending, mock_submit_async):
    mock_prime.return_value = {"username": "LINEユーザー", "detected_language": "ja"}
    mock_pending.return_value = {"user_message": "頭痛", "ai_response": "おすすめ"}
    with patch("src.handlers.line.line_reply.reply_messages", new_callable=AsyncMock) as mock_reply:
        asyncio.run(handle_line_feedback_postback("U1", "mrcfb|pos|abc12345", reply_token="tok"))
    mock_submit_async.assert_called_once()
    assert mock_submit_async.call_args.kwargs["report_type"] == "positive_feedback"
    assert mock_submit_async.call_args.kwargs["metadata"]["source"] == "line"
    mock_reply.assert_awaited_once()


@patch("src.handlers.line.line_feedback._load_pending_context", return_value=None)
@patch("src.handlers.line.line_session.prime_line_session")
@patch("config.line_config.LINE_CHANNEL_ACCESS_TOKEN", "token")
def test_handle_postback_replies_when_expired(mock_prime, mock_pending):
    mock_prime.return_value = {"username": "LINEユーザー", "detected_language": "ja"}
    with patch("src.handlers.line.line_reply.reply_messages", new_callable=AsyncMock) as mock_reply:
        asyncio.run(handle_line_feedback_postback("U1", "mrcfb|pos|abc12345", reply_token="tok"))
    mock_reply.assert_awaited_once()
    assert mock_reply.call_args[0][1][0]["text"] == "評価の有効期限が切れました。"


def test_should_offer_line_feedback_skips_security_responses():
    assert not should_offer_line_feedback(
        {"diagnosis": {"kind": "aggressive_input", "show_feedback": False}}
    )
    assert should_offer_line_feedback({"diagnosis": {"kind": "session_summary", "show_feedback": True}})


@patch("src.handlers.line.line_feedback._persist_pending_map")
def test_prepare_line_messages_skips_feedback_for_security_bot(mock_persist):
    bot = {"diagnosis": {"kind": "aggressive_input", "show_feedback": False, "message": "x"}}
    flex = [{"type": "flex", "altText": "notice"}]
    out = prepare_line_messages_with_feedback(
        flex,
        sid="line:U1",
        user_message="しね",
        bot_message=bot,
        lang="ja",
    )
    assert "quickReply" not in out[0]
    mock_persist.assert_not_called()


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


@patch("src.handlers.line.line_feedback._db_usable", return_value=True)
@patch("src.handlers.line.line_feedback._get_database")
def test_persist_pending_map_writes_db(mock_get_db, _mock_usable):
    from src.handlers.line.line_feedback import _persist_pending_map

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    pending = {"abc": {"user_message": "a", "ai_response": "b", "ts": time.time()}}
    _persist_pending_map("line:U1", pending)
    mock_db.set_line_feedback_pending.assert_called_once()
    assert mock_db.set_line_feedback_pending.call_args[0][0] == "line:U1"
    assert "abc" in mock_db.set_line_feedback_pending.call_args[0][1]
