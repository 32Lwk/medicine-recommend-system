"""配信アダプタテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.adapters.line_delivery import (
    build_line_delivery_envelope,
    resolve_line_messages,
    should_skip_redirect_on_missing_bot,
)
from src.dialogue.adapters.web_sse import (
    merge_dialogue_delivery_into_done,
    record_pipeline_envelope,
)
from src.dialogue.envelope import ENVELOPE_SESSION_KEY


def test_should_skip_redirect_on_missing():
    assert should_skip_redirect_on_missing_bot({"_pipeline_end_guard": "missing"}) is True
    assert should_skip_redirect_on_missing_bot({}) is False


@patch("src.dialogue.adapters.web_sse.is_chat_pipeline_v2_for_session", return_value=True)
def test_record_pipeline_envelope_web(_v2):
    session: dict = {}
    record_pipeline_envelope(session, "web-1", ({"status": "ok"}, 200))
    assert ENVELOPE_SESSION_KEY in session
    assert session[ENVELOPE_SESSION_KEY]["delivery_mode"] == "sync"


@patch("src.dialogue.adapters.web_sse.is_chat_pipeline_v2_for_session", return_value=True)
def test_merge_dialogue_delivery_into_done(_v2):
    session = {
        ENVELOPE_SESSION_KEY: {
            "delivery_mode": "sse_phased",
            "sse_phase_count": 2,
            "line_message_count": 0,
        }
    }
    out = merge_dialogue_delivery_into_done({"status": "ok"}, session, "web-1")
    assert out["dialogue_delivery"]["delivery_mode"] == "sse_phased"


@patch("src.handlers.line.flex_messages.build_line_messages_from_bot_message")
@patch("src.handlers.line.line_quick_actions.attach_session_quick_actions")
def test_build_line_delivery_envelope(mock_qr, mock_build):
    mock_build.return_value = [{"type": "text", "text": "hi"}]
    mock_qr.return_value = [{"type": "text", "text": "hi"}]
    bot = {"type": "bot", "content": "hello"}
    session: dict = {"messages": [bot]}
    env = build_line_delivery_envelope(bot, session, "line:U1", "ja")
    assert env.delivery_mode == "line_chunked"
    assert len(env.line_messages) == 1


@patch("src.dialogue.adapters.line_delivery.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.adapters.line_delivery.build_line_delivery_envelope")
def test_resolve_line_messages_stores_envelope(mock_build, _v2):
    from src.dialogue.envelope import ResponseEnvelope

    mock_build.return_value = ResponseEnvelope(
        delivery_mode="line_chunked",
        body={"status": "ok"},
        line_messages=[{"type": "text", "text": "x"}],
    )
    session: dict = {"messages": []}
    msgs = resolve_line_messages({"type": "bot"}, session, "line:U1", "ja")
    assert len(msgs) == 1
    assert ENVELOPE_SESSION_KEY in session
