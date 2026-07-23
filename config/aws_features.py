"""
AWS / Cloudflare 機能フラグ（環境変数）

GCP 本番（Cloud Run）では原則未設定 = レガシー挙動（DeepL / Web Speech / ローカル Concierge KB）。
AWS ステージング（ECS）のタスク定義でのみ AWS 向け値を設定する。

詳細: docs/ops/AWS_FEATURES_ROLLOUT.md
"""
from __future__ import annotations

import os

TRANSLATION_PROVIDER_DEEPL = "deepl"
TRANSLATION_PROVIDER_AWS = "translate"

CONCIERGE_RAG_LOCAL = "local"
CONCIERGE_RAG_BEDROCK = "bedrock_kb"

TTS_PROVIDER_WEBSPEECH = "webspeech"
TTS_PROVIDER_POLLY = "polly"


def _env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip()


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def get_translation_provider() -> str:
    """deepl（既定）| translate（AWS Translate）"""
    p = _env("TRANSLATION_PROVIDER", TRANSLATION_PROVIDER_DEEPL).lower()
    if p in (TRANSLATION_PROVIDER_AWS, "aws", "amazon"):
        return TRANSLATION_PROVIDER_AWS
    return TRANSLATION_PROVIDER_DEEPL


def use_aws_translate() -> bool:
    return get_translation_provider() == TRANSLATION_PROVIDER_AWS


def get_concierge_rag_provider() -> str:
    p = _env("CONCIERGE_RAG_PROVIDER", CONCIERGE_RAG_LOCAL).lower()
    if p in (CONCIERGE_RAG_BEDROCK, "bedrock", "kb"):
        return CONCIERGE_RAG_BEDROCK
    return CONCIERGE_RAG_LOCAL


def use_bedrock_kb_rag() -> bool:
    return get_concierge_rag_provider() == CONCIERGE_RAG_BEDROCK


def get_tts_provider() -> str:
    p = _env("TTS_PROVIDER", TTS_PROVIDER_WEBSPEECH).lower()
    if p == TTS_PROVIDER_POLLY:
        return TTS_PROVIDER_POLLY
    return TTS_PROVIDER_WEBSPEECH


def use_polly_tts() -> bool:
    return get_tts_provider() == TTS_PROVIDER_POLLY


def is_comprehend_medical_enabled() -> bool:
    return _flag("COMPREHEND_MEDICAL_ENABLED", False)


def get_redis_url() -> str:
    return _env("REDIS_URL")


def get_personalize_campaign_arn() -> str:
    return _env("PERSONALIZE_CAMPAIGN_ARN")


def get_personalize_tracking_id() -> str:
    """Personalize Event Tracker の tracking ID（put_events 用）。"""
    return _env("PERSONALIZE_TRACKING_ID")


def get_medicine_image_cdn_base() -> str:
    """例: https://images.yutok.dev/otc/ （末尾スラッシュ付き）"""
    base = _env("MEDICINE_IMAGE_CDN_BASE")
    if not base:
        return ""
    return base.rstrip("/") + "/"


def get_static_cdn_base_url() -> str:
    """AWS ステージング向け static/ CDN（CloudFront）。未設定時は空。"""
    return _env("STATIC_CDN_BASE_URL").rstrip("/")


def resolve_static_asset_url(filename: str) -> str:
    """Jinja url_for('static') 互換。STATIC_CDN_BASE_URL 設定時は CloudFront 直リンク。"""
    fn = (filename or "").lstrip("/")
    base = get_static_cdn_base_url()
    if base:
        return f"{base}/{fn}"
    return f"/static/{fn}"


def get_bedrock_kb_id() -> str:
    return _env("BEDROCK_KB_ID")


def get_aws_region() -> str:
    return _env("AWS_REGION", _env("AWS_DEFAULT_REGION", "ap-northeast-1"))


def is_aws_staging_site() -> bool:
    """AWS ステージング（aws.medicine.yutok.dev）判定。PUBLIC_SITE_URL または AWS_STAGING=1。"""
    url = _env("PUBLIC_SITE_URL", "").lower()
    if "aws.medicine" in url:
        return True
    return _flag("AWS_STAGING", False)


def is_concierge_technical_reference_enabled() -> bool:
    """Concierge が API/SSE/ルールベース等の技術詳細を参照に含めてよい環境。"""
    from config.app_config import is_development_runtime

    return is_development_runtime() or is_aws_staging_site()
