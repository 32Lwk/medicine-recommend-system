"""Google Cloud Text-to-Speech 合成。"""
from __future__ import annotations

import pytest


def test_google_tts_requires_flag(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "webspeech")
    from src.services.google_tts import synthesize_speech_mp3

    with pytest.raises(RuntimeError, match="not google"):
        synthesize_speech_mp3("hello")


def test_google_tts_synthesize_mock(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google")

    class _FakeResponse:
        audio_content = b"mp3-google"

    class _FakeClient:
        def synthesize_speech(self, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(
        "google.cloud.texttospeech.TextToSpeechClient",
        lambda: _FakeClient(),
    )
    from src.services.google_tts import synthesize_speech_mp3

    out = synthesize_speech_mp3("テスト", "ja")
    assert out == b"mp3-google"


def test_google_voice_for_lang():
    from src.services.google_tts import google_voice_for_lang

    assert google_voice_for_lang("ja") == "ja-JP-Neural2-B"
    assert google_voice_for_lang("en") == "en-US-Neural2-F"
