"""Amazon Polly TTS（AWS ステージング向け）。"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_VOICE_BY_LANG = {
    "ja": ("Mizuki", "neural"),
    "en": ("Joanna", "neural"),
    "ko": ("Seoyeon", "neural"),
    "zh": ("Zhiyu", "neural"),
}


def synthesize_speech_mp3(text: str, lang: str = "ja") -> bytes:
    from config.aws_features import get_aws_region, use_polly_tts

    if not use_polly_tts():
        raise RuntimeError("TTS_PROVIDER is not polly")
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("text is empty")

    import boto3

    code = (lang or "ja").strip().lower()[:2]
    voice_id, engine = _VOICE_BY_LANG.get(code, _VOICE_BY_LANG["ja"])
    client = boto3.client("polly", region_name=get_aws_region())
    try:
        resp = client.synthesize_speech(
            Text=cleaned[:3000],
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine=engine,
        )
    except Exception:
        logger.warning("Polly neural unavailable for %s, falling back to standard", voice_id)
        resp = client.synthesize_speech(
            Text=cleaned[:3000],
            OutputFormat="mp3",
            VoiceId=voice_id,
        )
    stream = resp.get("AudioStream")
    if stream is None:
        raise RuntimeError("Polly returned no audio stream")
    return stream.read()


def polly_voice_for_lang(lang: str) -> Optional[str]:
    code = (lang or "ja").strip().lower()[:2]
    entry = _VOICE_BY_LANG.get(code)
    return entry[0] if entry else None
