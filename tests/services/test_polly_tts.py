"""Polly TTS 合成（SSML 経路）。"""
from unittest.mock import MagicMock

import pytest


def test_synthesize_speech_mp3_uses_ssml_by_default(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "polly")
    monkeypatch.setenv("POLLY_SSML", "1")

    captured: dict = {}

    def _fake_client(*_args, **_kwargs):
        client = MagicMock()

        def _synthesize_speech(**kwargs):
            captured.update(kwargs)
            return {"AudioStream": MagicMock(read=lambda: b"mp3")}

        client.synthesize_speech = _synthesize_speech
        return client

    monkeypatch.setattr("boto3.client", _fake_client)

    from src.services.polly_tts import synthesize_speech_mp3

    out = synthesize_speech_mp3("こんにちは。テストです。", lang="ja")
    assert out == b"mp3"
    assert captured.get("TextType") == "ssml"
    assert captured.get("Text", "").startswith("<speak>")
    assert "<break time=\"450ms\"/>" in captured.get("Text", "")


def test_synthesize_speech_mp3_plain_when_ssml_disabled(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "polly")
    monkeypatch.setenv("POLLY_SSML", "0")

    captured: dict = {}

    def _fake_client(*_args, **_kwargs):
        client = MagicMock()

        def _synthesize_speech(**kwargs):
            captured.update(kwargs)
            return {"AudioStream": MagicMock(read=lambda: b"plain")}

        client.synthesize_speech = _synthesize_speech
        return client

    monkeypatch.setattr("boto3.client", _fake_client)

    from src.services.polly_tts import synthesize_speech_mp3

    out = synthesize_speech_mp3("プレーン", lang="ja")
    assert out == b"plain"
    assert captured.get("TextType") == "text"
    assert captured.get("Text") == "プレーン"
