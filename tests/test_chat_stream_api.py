"""SSE chat stream API"""
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
