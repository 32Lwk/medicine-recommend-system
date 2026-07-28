"""TTS プロバイダー振り分け（Polly / Google Cloud TTS）。"""
from __future__ import annotations


def synthesize_speech_mp3(text: str, lang: str = "ja") -> bytes:
    from config.aws_features import get_tts_provider, use_google_tts, use_polly_tts

    if use_polly_tts():
        from src.services.polly_tts import synthesize_speech_mp3 as polly_synthesize

        return polly_synthesize(text, lang)
    if use_google_tts():
        from src.services.google_tts import synthesize_speech_mp3 as google_synthesize

        return google_synthesize(text, lang)
    raise RuntimeError(f"TTS_PROVIDER is not a server provider: {get_tts_provider()}")


def server_tts_credentials_available() -> bool:
    from config.aws_features import use_google_tts, use_polly_tts

    if use_polly_tts():
        from src.services.polly_tts import polly_credentials_available

        return polly_credentials_available()
    if use_google_tts():
        from src.services.google_tts import google_tts_credentials_available

        return google_tts_credentials_available()
    return False
