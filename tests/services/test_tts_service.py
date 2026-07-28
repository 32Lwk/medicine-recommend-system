"""TTS プロバイダー振り分け。"""
from __future__ import annotations


def test_tts_service_routes_to_google(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google")

    called = {}

    def _fake(text, lang="ja"):
        called["text"] = text
        called["lang"] = lang
        return b"google-mp3"

    monkeypatch.setattr("src.services.google_tts.synthesize_speech_mp3", _fake)
    from src.services.tts_service import synthesize_speech_mp3

    assert synthesize_speech_mp3("こんにちは", "ja") == b"google-mp3"
    assert called == {"text": "こんにちは", "lang": "ja"}


def test_tts_service_routes_to_polly(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "polly")

    monkeypatch.setattr(
        "src.services.polly_tts.synthesize_speech_mp3",
        lambda text, lang="ja": b"polly-mp3",
    )
    from src.services.tts_service import synthesize_speech_mp3

    assert synthesize_speech_mp3("hello", "en") == b"polly-mp3"
