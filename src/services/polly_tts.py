"""Amazon Polly TTS（AWS ステージング向け）。"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_VOICE_BY_LANG = {
    "ja": ("Mizuki", "neural"),
    "en": ("Joanna", "neural"),
    "ko": ("Seoyeon", "neural"),
    "zh": ("Zhiyu", "neural"),
}


def polly_credentials_available() -> bool:
    """ローカル等で AWS 資格情報が無い場合は False。"""
    try:
        import boto3

        return boto3.Session().get_credentials() is not None
    except Exception:
        return False


def _synthesize_once(
    client: Any,
    *,
    text: str,
    text_type: str,
    voice_id: str,
    engine: Optional[str],
) -> bytes:
    kwargs: dict[str, Any] = {
        "Text": text,
        "TextType": text_type,
        "OutputFormat": "mp3",
        "VoiceId": voice_id,
    }
    if engine:
        kwargs["Engine"] = engine
    resp = client.synthesize_speech(**kwargs)
    stream = resp.get("AudioStream")
    if stream is None:
        raise RuntimeError("Polly returned no audio stream")
    return stream.read()


def synthesize_speech_mp3(text: str, lang: str = "ja") -> bytes:
    from config.aws_features import get_aws_region, use_polly_tts
    from src.services.polly_ssml import build_polly_ssml, polly_ssml_enabled

    if not use_polly_tts():
        raise RuntimeError("TTS_PROVIDER is not polly")
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("text is empty")

    import boto3

    code = (lang or "ja").strip().lower()[:2]
    voice_id, engine = _VOICE_BY_LANG.get(code, _VOICE_BY_LANG["ja"])
    client = boto3.client("polly", region_name=get_aws_region())

    use_ssml = polly_ssml_enabled()
    ssml = build_polly_ssml(cleaned, lang=code) if use_ssml else cleaned[:3000]
    text_type = "ssml" if use_ssml else "text"
    payload = ssml if use_ssml else cleaned[:3000]

    try:
        return _synthesize_once(
            client,
            text=payload,
            text_type=text_type,
            voice_id=voice_id,
            engine=engine,
        )
    except Exception as first_exc:
        if use_ssml:
            logger.warning("Polly SSML synthesis failed, retrying plain text: %s", first_exc)
            try:
                return _synthesize_once(
                    client,
                    text=cleaned[:3000],
                    text_type="text",
                    voice_id=voice_id,
                    engine=engine,
                )
            except Exception:
                logger.warning(
                    "Polly neural unavailable for %s, falling back to standard",
                    voice_id,
                )
                return _synthesize_once(
                    client,
                    text=cleaned[:3000],
                    text_type="text",
                    voice_id=voice_id,
                    engine=None,
                )
        logger.warning("Polly neural unavailable for %s, falling back to standard", voice_id)
        try:
            return _synthesize_once(
                client,
                text=cleaned[:3000],
                text_type="text",
                voice_id=voice_id,
                engine=None,
            )
        except Exception as exc:
            raise first_exc from exc


def polly_voice_for_lang(lang: str) -> Optional[str]:
    code = (lang or "ja").strip().lower()[:2]
    entry = _VOICE_BY_LANG.get(code)
    return entry[0] if entry else None
