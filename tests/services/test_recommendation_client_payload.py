"""recommendation_client_payload helpers."""
from __future__ import annotations

from src.services.recommendation_client_payload import should_skip_reco_progressive_sse


def test_should_skip_reco_progressive_sse_sage_web():
    assert should_skip_reco_progressive_sse({"ui_variant": "sage"}, "123456") is True


def test_should_skip_reco_progressive_sse_line_when_reply_stream_enabled(monkeypatch):
    monkeypatch.setattr("src.services.sse_emit.reply_stream_sse_enabled", lambda: True)
    assert should_skip_reco_progressive_sse({"ui_variant": "sage"}, "line:Uabc") is False


def test_should_skip_reco_progressive_sse_line_when_reply_stream_disabled(monkeypatch):
    monkeypatch.setattr("src.services.sse_emit.reply_stream_sse_enabled", lambda: False)
    assert should_skip_reco_progressive_sse({"ui_variant": "sage"}, "line:Uabc") is True


def test_should_skip_reco_progressive_sse_no_sid_when_reply_stream_disabled(monkeypatch):
    monkeypatch.setattr("src.services.sse_emit.reply_stream_sse_enabled", lambda: False)
    assert should_skip_reco_progressive_sse({"ui_variant": "sage"}, None) is True


def test_should_skip_reco_progressive_sse_no_sid_when_reply_stream_enabled(monkeypatch):
    monkeypatch.setattr("src.services.sse_emit.reply_stream_sse_enabled", lambda: True)
    assert should_skip_reco_progressive_sse({"ui_variant": "sage"}, None) is False
