"""config/aws_features.py の既定値（GCP 本番 = レガシー）。"""
import pytest

from config import aws_features


@pytest.fixture(autouse=True)
def _clear_aws_env(monkeypatch):
    for key in (
        "TRANSLATION_PROVIDER",
        "CONCIERGE_RAG_PROVIDER",
        "MEDICINE_RAG_PROVIDER",
        "TTS_PROVIDER",
        "COMPREHEND_MEDICAL_ENABLED",
        "REDIS_URL",
        "PERSONALIZE_CAMPAIGN_ARN",
        "MEDICINE_IMAGE_CDN_BASE",
        "STATIC_CDN_BASE_URL",
        "BEDROCK_KB_ID",
        "BEDROCK_MEDICINE_KB_ID",
        "BEDROCK_KB_SEARCH_MODE",
        "PUBLIC_SITE_URL",
        "AWS_STAGING",
        "APP_ENV",
    ):
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_legacy():
    assert aws_features.get_translation_provider() == "deepl"
    assert not aws_features.use_aws_translate()
    assert aws_features.get_concierge_rag_provider() == "local"
    assert not aws_features.use_bedrock_kb_rag()
    assert not aws_features.use_medicine_bedrock_kb_rag()
    assert aws_features.get_tts_provider() == "webspeech"
    assert not aws_features.use_polly_tts()
    assert not aws_features.is_comprehend_medical_enabled()
    assert aws_features.get_medicine_image_cdn_base() == ""


def test_static_cdn_url_resolution(monkeypatch):
    monkeypatch.setenv("STATIC_CDN_BASE_URL", "https://d111111.cloudfront.net/static")
    from config.aws_features import resolve_static_asset_url

    assert resolve_static_asset_url("css/main.css") == "https://d111111.cloudfront.net/static/css/main.css"
    assert resolve_static_asset_url("/js/main.js") == "https://d111111.cloudfront.net/static/js/main.js"


def test_static_cdn_unset_uses_local_path(monkeypatch):
    monkeypatch.delenv("STATIC_CDN_BASE_URL", raising=False)
    from config.aws_features import resolve_static_asset_url

    assert resolve_static_asset_url("css/main.css") == "/static/css/main.css"


def test_aws_staging_flags(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "translate")
    monkeypatch.setenv("TTS_PROVIDER", "polly")
    monkeypatch.setenv("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc")
    assert aws_features.use_aws_translate()
    assert aws_features.use_polly_tts()
    assert aws_features.get_medicine_image_cdn_base() == "https://images.yutok.dev/otc/"


def test_is_aws_staging_site_from_public_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://aws.medicine.yutok.dev")
    assert aws_features.is_aws_staging_site()


def test_concierge_technical_reference_on_aws_staging(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://aws.medicine.yutok.dev")
    assert aws_features.is_concierge_technical_reference_enabled()
