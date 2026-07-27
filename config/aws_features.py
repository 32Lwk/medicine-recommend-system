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
CONCIERGE_RAG_NONE = "none"

MEDICINE_RAG_LOCAL = "local"
MEDICINE_RAG_BEDROCK = "bedrock_kb"
MEDICINE_RAG_NONE = "none"

BEDROCK_KB_SEARCH_MANAGED = "managed"
BEDROCK_KB_SEARCH_VECTOR = "vector"

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
    if p in (CONCIERGE_RAG_NONE, "off", "false", "0", "disabled"):
        return CONCIERGE_RAG_NONE
    return CONCIERGE_RAG_LOCAL


def use_bedrock_kb_rag() -> bool:
    return get_concierge_rag_provider() == CONCIERGE_RAG_BEDROCK


def get_medicine_rag_provider() -> str:
    p = _env("MEDICINE_RAG_PROVIDER", MEDICINE_RAG_LOCAL).lower()
    if p in (MEDICINE_RAG_BEDROCK, "bedrock", "kb"):
        return MEDICINE_RAG_BEDROCK
    if p in (MEDICINE_RAG_NONE, "off", "false", "0", "disabled"):
        return MEDICINE_RAG_NONE
    return MEDICINE_RAG_LOCAL


def use_medicine_bedrock_kb_rag() -> bool:
    return get_medicine_rag_provider() == MEDICINE_RAG_BEDROCK


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
    # Cloud Run 等で env 未注入時のフォールバック（cloudbuild.yaml と同一 CDN）
    if not base and os.getenv("K_SERVICE"):
        base = "https://images.yutok.dev/otc/"
    if not base:
        return ""
    return base.rstrip("/") + "/"


def get_static_cdn_base_url() -> str:
    """AWS ステージング向け static/ CDN（CloudFront）。未設定時は空。"""
    return _env("STATIC_CDN_BASE_URL").rstrip("/")


def resolve_static_asset_url(filename: str) -> str:
    """Jinja url_for('static') 互換。CDN 設定時も localhost では /static/ を優先。"""
    fn = (filename or "").lstrip("/")
    from config.static_assets import should_prefer_local_static_assets

    if should_prefer_local_static_assets():
        return f"/static/{fn}"
    base = get_static_cdn_base_url()
    if base:
        return f"{base}/{fn}"
    return f"/static/{fn}"


def get_bedrock_kb_id() -> str:
    return _env("BEDROCK_KB_ID")


def get_bedrock_medicine_kb_id() -> str:
    return _env("BEDROCK_MEDICINE_KB_ID")


def get_bedrock_kb_search_mode() -> str:
    """
    Bedrock KB retrieve API モード。
    managed: Managed KB（managedSearchConfiguration）
    vector: Customer-managed KB（vectorSearchConfiguration）
    """
    mode = _env("BEDROCK_KB_SEARCH_MODE", BEDROCK_KB_SEARCH_MANAGED).lower()
    if mode in (BEDROCK_KB_SEARCH_VECTOR, "customer", "opensearch"):
        return BEDROCK_KB_SEARCH_VECTOR
    return BEDROCK_KB_SEARCH_MANAGED


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
