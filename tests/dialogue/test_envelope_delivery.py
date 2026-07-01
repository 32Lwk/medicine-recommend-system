"""ResponseEnvelope 配信モードテスト。"""
from __future__ import annotations

from src.dialogue.envelope import ResponseEnvelope


def test_envelope_web_sync():
    env = ResponseEnvelope.wrap_session_ops(({"status": "ok"}, 200), sid="web-abc")
    assert env.delivery_mode == "sync"
    assert env.to_response_tuple() == ({"status": "ok"}, 200)


def test_envelope_line_chunked():
    env = ResponseEnvelope.wrap_session_ops(({"status": "ok"}, 200), sid="line:U1")
    assert env.delivery_mode == "line_chunked"


def test_envelope_sse_phases():
    env = ResponseEnvelope.from_http_response(
        ({"status": "ok"}, 200),
        channel="web",
        sse_phases=[{"phase": "cards"}],
    )
    assert env.delivery_mode == "sse_phased"
    assert env.sse_phases[0]["phase"] == "cards"
