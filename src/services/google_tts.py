"""Google Cloud Text-to-Speech（GCP Cloud Run 本番・dev 向け）。"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# (language_code, voice_name)
_VOICE_BY_LANG = {
    "ja": ("ja-JP", "ja-JP-Neural2-B"),
    "en": ("en-US", "en-US-Neural2-F"),
    "ko": ("ko-KR", "ko-KR-Neural2-A"),
    "zh": ("cmn-CN", "cmn-CN-Wavenet-A"),
}


def google_tts_credentials_available() -> bool:
    """ADC / サービスアカウントが利用可能か。"""
    try:
        import google.auth

        creds, _project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return creds is not None
    except Exception:
        return False


def synthesize_speech_mp3(text: str, lang: str = "ja") -> bytes:
    from config.aws_features import use_google_tts
    from src.services.polly_ssml import build_polly_ssml, polly_ssml_enabled

    if not use_google_tts():
        raise RuntimeError("TTS_PROVIDER is not google")
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("text is empty")

    from google.cloud import texttospeech

    code = (lang or "ja").strip().lower()[:2]
    language_code, voice_name = _VOICE_BY_LANG.get(code, _VOICE_BY_LANG["ja"])
    client = texttospeech.TextToSpeechClient()

    use_ssml = polly_ssml_enabled()
    if use_ssml:
        payload = build_polly_ssml(cleaned, lang=code)
        synthesis_input = texttospeech.SynthesisInput(ssml=payload)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=cleaned[:3000])

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
    except Exception as first_exc:
        if use_ssml:
            logger.warning("Google TTS SSML synthesis failed, retrying plain text: %s", first_exc)
            synthesis_input = texttospeech.SynthesisInput(text=cleaned[:3000])
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
        else:
            raise
    content = response.audio_content
    if not content:
        raise RuntimeError("Google TTS returned no audio content")
    return bytes(content)


def google_voice_for_lang(lang: str) -> Optional[str]:
    code = (lang or "ja").strip().lower()[:2]
    entry = _VOICE_BY_LANG.get(code)
    return entry[1] if entry else None
