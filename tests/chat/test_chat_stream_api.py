"""SSE chat stream API"""
from unittest.mock import patch

from src.handlers.chat_stream import _extract_done_messages
from src.handlers.sse_events import SseDoneEvent


def _sse_line(event, data, event_id=None):
    import json

    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def test_sse_line_format():
    line = _sse_line("advice_delta", {"text": "あ"}, event_id="42")
    assert "event: advice_delta" in line
    assert "id: 42" in line
    assert '"あ"' in line


def test_sse_done_payload_trace():
    payload = SseDoneEvent(http_status=200, status="ok", message_count=2, trace_id="t-99").to_payload()
    assert payload["trace_id"] == "t-99"
    assert payload["message_count"] == 2


def test_sse_done_payload_includes_bot_message():
    bot = {"type": "bot", "content": "案内です", "store_inquiry": True}
    user = {"type": "user", "content": "トイレはどこ？"}
    payload = SseDoneEvent(
        message_count=2,
        bot_message=bot,
        user_message=user,
    ).to_payload()
    assert payload["bot_message"] == bot
    assert payload["user_message"] == user


def test_sse_done_payload_includes_dev_error_fields():
    payload = SseDoneEvent(
        http_status=200,
        message_count=1,
        error=True,
        response="【開発プレビュー】クライアント側のエラーカード表示です。",
        dev_preview_kind="client_error",
    ).to_payload()
    assert payload["error"] is True
    assert "開発プレビュー" in payload["response"]
    assert payload["dev_preview_kind"] == "client_error"


def test_build_sse_done_event_from_dev_client_error():
    from src.handlers.chat_stream import _build_sse_done_event

    body = {
        "error": True,
        "response": "【開発プレビュー】クライアント側のエラーカード表示です。",
        "message_count": 1,
        "dev_preview_kind": "client_error",
    }
    messages = [{"type": "user", "content": "mrcdev00000000000001"}]
    done = _build_sse_done_event(body, 200, messages)
    payload = done.to_payload()
    assert payload["error"] is True
    assert payload["message_count"] == 1
    assert "bot_message" not in payload
    assert payload["dev_preview_kind"] == "client_error"


def test_sse_stream_emits_client_preview_before_done():
    import re
    from unittest.mock import patch
    from starlette.testclient import TestClient
    import main

    with patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True):
        with patch("src.handlers.chat.chat_dev_triggers.save_session_to_db"):
            with patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None):
                with TestClient(main.app) as client:
                    response = client.post(
                        "/api/chat/stream",
                        data={"message": "mrcdev00000000000001"},
                        headers={"Accept": "text/event-stream"},
                    )
                    assert response.status_code == 200
                    text = response.text
                    preview_match = re.search(r"event: client_preview\s*\ndata: (.+)", text)
                    done_match = re.search(r"event: done\s*\ndata: (.+)", text)
                    assert preview_match is not None
                    assert done_match is not None
                    assert text.index("event: client_preview") < text.index("event: done")
                    assert '"error": true' in preview_match.group(1) or '"error":true' in preview_match.group(1)


def test_extract_done_messages_when_last_is_bot():
    messages = [
        {"type": "user", "content": "こんにちは"},
        {"type": "bot", "content": "返信", "counseling": True},
    ]
    bot, user = _extract_done_messages(messages)
    assert bot["content"] == "返信"
    assert user["content"] == "こんにちは"


def test_extract_done_messages_when_trailing_user():
    messages = [
        {"type": "user", "content": "a"},
        {"type": "bot", "content": "返信", "counseling": True},
        {"type": "user", "content": "a"},
    ]
    bot, user = _extract_done_messages(messages)
    assert bot["content"] == "返信"
    assert user["content"] == "a"


def test_messages_for_sse_done_falls_back_to_db_when_session_empty():
    from src.handlers.chat_stream import _build_sse_done_event, _messages_for_sse_done

    bot = {
        "type": "bot",
        "content": "sage_qa",
        "diagnosis": {"render": "sage_qa", "message": "回答"},
    }
    user = {"type": "user", "content": "ロキソニンって眠くなる？"}
    db_messages = [user, bot]
    session = {}

    with patch("src.handlers.chat_stream.get_session_from_db", return_value={"messages": db_messages}):
        messages = _messages_for_sse_done(session, "sid1", {"status": "ok", "message_count": 2})

    assert messages == db_messages
    done = _build_sse_done_event({"status": "ok", "message_count": 2}, 200, messages)
    payload = done.to_payload()
    assert payload["bot_message"] == bot
    assert payload["diagnosis"]["render"] == "sage_qa"
