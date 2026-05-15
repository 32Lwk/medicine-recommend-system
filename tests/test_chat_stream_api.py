"""SSE chat stream API"""
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
