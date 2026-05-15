"""chat_post_pipeline のスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_post_pipeline import ChatPostContext, run_chat_post_pipeline
from src.utils.chat_http_context import ChatClientInfo


def test_empty_message_short_circuit():
    session = {"messages": []}
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    with patch(
        "src.handlers.chat.chat_post_pipeline.empty_message_response",
        return_value=({"status": "ok", "message_count": 0}, 200),
    ):
        resp = run_chat_post_pipeline(session, client, "", "sid", MagicMock())
    assert resp[0]["status"] == "ok"


def test_context_dataclass_defaults():
    ctx = ChatPostContext(
        session={},
        client_info=ChatClientInfo(client_ip="1", user_agent="t"),
        sid=None,
        monitor=MagicMock(),
        user_agent="t",
        client_ip="1",
    )
    assert ctx.triage_result is None
    assert ctx.inappropriate_request_detected is False
