"""POST /api/tts — Polly ゲート。"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_tts_not_available_by_default(client, monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "webspeech")
    r = client.post("/api/tts", json={"text": "hello", "lang": "ja"})
    assert r.status_code == 404


def test_tts_polly_mock(client, monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "polly")
    monkeypatch.setattr("src.services.tts_service.server_tts_credentials_available", lambda: True)

    def _fake(text, lang="ja"):
        assert text == "テスト"
        return b"mp3-bytes"

    monkeypatch.setattr("src.services.tts_service.synthesize_speech_mp3", _fake)
    r = client.post("/api/tts", json={"text": "テスト", "lang": "ja"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"mp3-bytes"


def test_tts_google_mock(client, monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google")
    monkeypatch.setattr("src.services.tts_service.server_tts_credentials_available", lambda: True)
    monkeypatch.setattr(
        "src.services.tts_service.synthesize_speech_mp3",
        lambda text, lang="ja": b"google-mp3",
    )
    r = client.post("/api/tts", json={"text": "テスト", "lang": "ja"})
    assert r.status_code == 200
    assert r.content == b"google-mp3"
